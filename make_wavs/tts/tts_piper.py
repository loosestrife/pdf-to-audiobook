import numpy as np

class PiperTTS:
    def __init__(self, model_path: str = "en_US-lessac-medium.onnx"):
        from piper import PiperVoice
        # Piper models run natively via ONNX
        self.voice = PiperVoice.load(model_path)
        self.sample_rate = self.voice.config.sample_rate

    def generate_samples(self, text: str):
        # Synthesize returns an iterator of audio raw bytes (int16)
        audio_bytes = b"".join(self.voice.synthesize_stream_raw(text))
        
        # Convert int16 raw PCM byte stream to float32 numpy array
        int_samples = np.frombuffer(audio_bytes, dtype=np.int16)
        float_samples = int_samples.astype(np.float32) / 32768.0
        
        return float_samples, self.sample_rate