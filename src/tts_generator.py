"""
Text-to-Speech Generator using Kokoro TTS

Generates audio files from text using the Kokoro TTS model.
Optimized for Apple Silicon (M-series) Macs.
"""

import os
import time
import numpy as np
import torch
import soundfile as sf
from typing import List, Optional, Callable
from dataclasses import dataclass


# Try to import kokoro
try:
    from kokoro import KPipeline
    KOKORO_AVAILABLE = True
except ImportError:
    KOKORO_AVAILABLE = False
    print("Warning: Kokoro not available. TTS will not work.")


# Configuration
DEFAULT_SAMPLE_RATE = 24000
DEVICE = "mps" if torch.backends.mps.is_available() else "cpu"


@dataclass
class TTSConfig:
    """Configuration for TTS generation."""
    voice: str = "af_heart"  # Default voice
    speed: float = 1.0
    lang_code: str = "a"  # 'a' for American English
    sample_rate: int = DEFAULT_SAMPLE_RATE
    output_format: str = ".wav"


# Available Kokoro voices for English
ENGLISH_VOICES = {
    # American Female
    "af_heart": "American Female - Heart (warm, friendly)",
    "af_alloy": "American Female - Alloy",
    "af_bella": "American Female - Bella",
    "af_jessica": "American Female - Jessica",
    "af_nicole": "American Female - Nicole",
    "af_nova": "American Female - Nova",
    "af_river": "American Female - River",
    "af_sarah": "American Female - Sarah",
    "af_sky": "American Female - Sky",
    # American Male
    "am_adam": "American Male - Adam",
    "am_echo": "American Male - Echo",
    "am_eric": "American Male - Eric",
    "am_liam": "American Male - Liam",
    "am_michael": "American Male - Michael",
    "am_onyx": "American Male - Onyx",
    # British Female
    "bf_alice": "British Female - Alice",
    "bf_emma": "British Female - Emma",
    "bf_isabella": "British Female - Isabella",
    "bf_lily": "British Female - Lily",
    # British Male
    "bm_daniel": "British Male - Daniel",
    "bm_fable": "British Male - Fable",
    "bm_george": "British Male - George",
    "bm_lewis": "British Male - Lewis",
}


def get_available_voices() -> dict:
    """Return available English voices."""
    return ENGLISH_VOICES


class KokoroTTSGenerator:
    """Text-to-Speech generator using Kokoro."""
    
    def __init__(self, config: Optional[TTSConfig] = None):
        if not KOKORO_AVAILABLE:
            raise RuntimeError("Kokoro TTS is not installed. Install with: pip install kokoro")
        
        self.config = config or TTSConfig()
        self.pipeline = None
        self._init_pipeline()
    
    def _init_pipeline(self):
        """Initialize the Kokoro pipeline."""
        print(f"Initializing Kokoro TTS on device: {DEVICE}")
        print(f"Voice: {self.config.voice}")
        start_time = time.time()
        
        self.pipeline = KPipeline(
            lang_code=self.config.lang_code,
            device=DEVICE,
            repo_id='hexgrad/Kokoro-82M'
        )
        
        print(f"Pipeline initialized in {time.time() - start_time:.2f}s")
    
    def generate_audio(
        self,
        text: str,
        output_path: str,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> bool:
        """
        Generate audio from text and save to file.
        
        Args:
            text: Text to convert to speech
            output_path: Path to save the audio file
            progress_callback: Optional callback(chars_processed, total_chars)
        
        Returns:
            True if successful, False otherwise
        """
        if not text.strip():
            print("Warning: Empty text provided")
            return False
        
        start_time = time.time()
        total_chars = len(text)
        chars_processed = 0
        audio_chunks = []
        
        try:
            # Generate audio in chunks
            for chunk_idx, (gs, ps, audio) in enumerate(
                self.pipeline(
                    text,
                    voice=self.config.voice,
                    speed=self.config.speed,
                    split_pattern=r'\n+'
                )
            ):
                # Convert to numpy if needed
                if isinstance(audio, torch.Tensor):
                    audio = audio.cpu().numpy()
                
                audio_chunks.append(audio)
                
                # Track progress
                if gs:
                    chars_processed += len(gs)
                    if progress_callback:
                        progress_callback(chars_processed, total_chars)
            
            if not audio_chunks:
                print("Warning: No audio generated")
                return False
            
            # Concatenate all chunks
            combined_audio = np.concatenate(audio_chunks)
            
            # Normalize to prevent clipping
            max_val = np.max(np.abs(combined_audio))
            if max_val > 0:
                normalized = (combined_audio / max_val * 32767 * 0.95).astype(np.int16)
            else:
                normalized = combined_audio.astype(np.int16)
            
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Save audio
            sf.write(output_path, normalized, self.config.sample_rate)
            
            duration = len(combined_audio) / self.config.sample_rate
            elapsed = time.time() - start_time
            print(f"Generated {duration:.1f}s audio in {elapsed:.1f}s (ratio: {duration/elapsed:.1f}x realtime)")
            
            return True
            
        except Exception as e:
            print(f"Error generating audio: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def generate_chapter_audio(
        self,
        chapter_text: str,
        chapter_title: str,
        output_path: str,
        add_title_announcement: bool = True
    ) -> bool:
        """
        Generate audio for a chapter with optional title announcement.
        
        Args:
            chapter_text: The chapter text content
            chapter_title: Title of the chapter
            output_path: Path to save the audio file
            add_title_announcement: Whether to prepend "Chapter: [title]" announcement
        
        Returns:
            True if successful
        """
        if add_title_announcement:
            # Create title announcement text
            announcement = f"Chapter: {chapter_title}.\n\n"
            full_text = announcement + chapter_text
        else:
            full_text = chapter_text
        
        return self.generate_audio(full_text, output_path)


def generate_audiobook(
    text_files: List[str],
    output_dir: str,
    voice: str = "af_heart",
    speed: float = 1.0,
    progress_callback: Optional[Callable[[int, int, str], None]] = None
) -> List[str]:
    """
    Generate audiobook from a list of text files.
    
    Args:
        text_files: List of paths to text files (chapters)
        output_dir: Directory to save audio files
        voice: Voice identifier
        speed: Speech speed multiplier
        progress_callback: Optional callback(current_file, total_files, filename)
    
    Returns:
        List of generated audio file paths
    """
    os.makedirs(output_dir, exist_ok=True)
    
    config = TTSConfig(voice=voice, speed=speed)
    generator = KokoroTTSGenerator(config)
    
    generated_files = []
    total_files = len(text_files)
    
    for i, text_file in enumerate(text_files, 1):
        filename = os.path.basename(text_file)
        print(f"\n[{i}/{total_files}] Processing: {filename}")
        
        if progress_callback:
            progress_callback(i, total_files, filename)
        
        # Read text file
        with open(text_file, 'r', encoding='utf-8') as f:
            text = f.read()
        
        if not text.strip():
            print(f"  Skipping empty file: {filename}")
            continue
        
        # Generate output filename
        base_name = os.path.splitext(filename)[0]
        output_path = os.path.join(output_dir, f"{base_name}.wav")
        
        # Generate audio
        success = generator.generate_audio(text, output_path)
        
        if success:
            generated_files.append(output_path)
            print(f"  Saved: {output_path}")
        else:
            print(f"  Failed to generate audio for: {filename}")
    
    return generated_files


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python tts_generator.py <input_text_file> <output_audio_file>")
        print("\nAvailable voices:")
        for voice_id, description in get_available_voices().items():
            print(f"  {voice_id}: {description}")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    voice = sys.argv[3] if len(sys.argv) > 3 else "af_heart"
    
    with open(input_file, 'r', encoding='utf-8') as f:
        text = f.read()
    
    config = TTSConfig(voice=voice)
    generator = KokoroTTSGenerator(config)
    success = generator.generate_audio(text, output_file)
    
    if success:
        print(f"Audio saved to: {output_file}")
    else:
        print("Failed to generate audio")
        sys.exit(1)
