import os
import re
import time
import numpy as np
import soundfile as sf
from typing import List, Optional, Callable
from dataclasses import dataclass
import asyncio

from .tts_kokoro import get_sample_generator
#import get_sample_generator from .tts_qwen3_tts
def generate_audio(text: str, output_path: str) -> bool:
    if not text.strip():
        return False
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    async def _stream_to_file():
        total_time = 0.0
        start_time = time.time()
        with sf.SoundFile(output_path, mode="w", samplerate=24000, channels=1) as f:
            async for samples, sample_rate in get_sample_generator(
                text
            ):
                if samples is not None and len(samples) > 0:
                    chunk_time = len(samples) / sample_rate
                    total_time += chunk_time
                    print(total_time, '(', chunk_time, ')', total_time/(time.time()-start_time))
                    max_val = np.max(np.abs(samples))
                    if max_val > 0:
                        normalized = (samples / max_val * 32767 * 0.95).astype(np.int16)
                    else:
                        normalized = samples.astype(np.int16)
                    f.write(normalized)
    try:
        asyncio.run(_stream_to_file())
        return True
    except Exception as e:
        print(f"Error synthesizing audio: {e}")
        return False


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


def generate_chapter_audio(
    chapter_text: str,
    chapter_title: str,
    output_path: str,
    add_title_announcement: bool = True
) -> bool:
    if add_title_announcement:
        announcement = f"Chapter: {chapter_title}.\n\n"
        full_text = announcement + chapter_text
    else:
        full_text = chapter_text
    
    return generate_audio(full_text, output_path)


def generate_audiobook(
    text_files: List[str],
    output_dir: str,
    voice: str = "af_heart",
    speed: float = 1.0,
    progress_callback: Optional[Callable[[int, int, str], None]] = None
) -> List[str]:
    os.makedirs(output_dir, exist_ok=True)
    
    
    generated_files = []
    total_files = len(text_files)
    
    for i, text_file in enumerate(text_files, 1):
        filename = os.path.basename(text_file)
        print(f"\n[{i}/{total_files}] Processing: {filename}")
        
        if progress_callback:
            progress_callback(i, total_files, filename)
        
        with open(text_file, 'r', encoding='utf-8') as f:
            text = f.read()
        
        if not text.strip():
            print(f"  Skipping empty file: {filename}")
            continue
        
        base_name = os.path.splitext(filename)[0]
        output_path = os.path.join(output_dir, f"{base_name}.wav")
        
        success = generate_audio(text, output_path)
        
        if success:
            generated_files.append(output_path)
            print(f"  Saved: {output_path}")
        else:
            print(f"  Failed to generate audio for: {filename}")
    
    return generated_files


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python tts_generator.py <input_text_file> <output_audio_file> [voice]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    voice_choice = sys.argv[3] if len(sys.argv) > 3 else "af_nova"
    
    with open(input_file, 'r', encoding='utf-8') as f:
        input_text = f.read()
    
    status = generate_audio(input_text, output_file)
    
    if status:
        print(f"Audio saved to: {output_file}")
    else:
        print("Failed to generate audio")
        sys.exit(1)
