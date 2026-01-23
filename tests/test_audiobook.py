"""
Tests for PDF to Audiobook conversion.
"""

import os
import sys
import pytest
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestPDFExtractor:
    """Tests for PDF text extraction."""
    
    def test_normalize_text(self):
        from src.pdf_extractor import normalize_text
        
        # Test ligature replacement
        assert 'fi' in normalize_text('ﬁnd')
        assert 'fl' in normalize_text('ﬂow')
        assert 'ff' in normalize_text('ﬀ')
        assert 'ffi' in normalize_text('ﬃ')
        assert 'ffl' in normalize_text('ﬄ')
        
        # Test smart quotes
        assert '"' in normalize_text('"test"')
        assert "'" in normalize_text("'test'")
    
    def test_expand_abbreviations(self):
        from src.pdf_extractor import expand_abbreviations
        
        assert 'Mister' in expand_abbreviations('Mr. Smith')
        assert 'Doctor' in expand_abbreviations('Dr. Jones')
        assert 'and others' in expand_abbreviations('Smith et al.')
    
    def test_convert_numbers_to_words(self):
        from src.pdf_extractor import convert_numbers_to_words
        
        # Cardinal numbers
        result = convert_numbers_to_words('There were 5 people')
        assert 'five' in result.lower()
        
        # Years
        result = convert_numbers_to_words('In 1984')
        assert 'nineteen' in result.lower()
        
        # Ordinals
        result = convert_numbers_to_words('The 1st place')
        assert 'first' in result.lower()
    
    def test_clean_text_for_tts(self):
        from src.pdf_extractor import clean_text_for_tts
        
        # Combined cleaning
        text = clean_text_for_tts('Mr. Smith found 5 items.')
        assert 'Mister' in text
        assert 'five' in text.lower()


class TestTTSGenerator:
    """Tests for TTS generation."""
    
    def test_get_available_voices(self):
        from src.tts_generator import get_available_voices
        
        voices = get_available_voices()
        assert 'af_heart' in voices
        assert 'am_liam' in voices
        assert len(voices) >= 20
    
    def test_tts_config(self):
        from src.tts_generator import TTSConfig
        
        config = TTSConfig()
        assert config.voice == 'af_heart'
        assert config.speed == 1.0
        assert config.sample_rate == 24000


class TestAudiobookOutput:
    """Tests for verifying generated audiobook."""
    
    @pytest.fixture
    def audio_dir(self):
        return Path(__file__).parent.parent / 'output' / 'why-love-matters' / 'audio'
    
    def test_all_chapters_generated(self, audio_dir):
        """Verify all expected audio files exist."""
        if not audio_dir.exists():
            pytest.skip("Audiobook not yet generated")
        
        audio_files = list(audio_dir.glob('*.wav'))
        assert len(audio_files) == 16, f"Expected 16 chapters, found {len(audio_files)}"
    
    def test_audio_files_not_empty(self, audio_dir):
        """Verify audio files have content."""
        if not audio_dir.exists():
            pytest.skip("Audiobook not yet generated")
        
        for audio_file in audio_dir.glob('*.wav'):
            size = audio_file.stat().st_size
            assert size > 1000000, f"{audio_file.name} seems too small ({size} bytes)"
    
    def test_audio_duration_reasonable(self, audio_dir):
        """Verify audio durations are reasonable."""
        try:
            import soundfile as sf
        except ImportError:
            pytest.skip("soundfile not installed")
        
        if not audio_dir.exists():
            pytest.skip("Audiobook not yet generated")
        
        for audio_file in audio_dir.glob('*.wav'):
            info = sf.info(str(audio_file))
            # Each chapter should be at least 1 minute
            assert info.duration > 60, f"{audio_file.name} seems too short"
            # And less than 2 hours
            assert info.duration < 7200, f"{audio_file.name} seems too long"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
