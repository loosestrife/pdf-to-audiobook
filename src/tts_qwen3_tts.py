import os
import torch
import soundfile as sf
import numpy as np
from qwen_tts import Qwen3TTSModel

# 1. Environment configuration for AMD ROCm
device = "cuda" if torch.cuda.is_available() else "cpu"
dtype = torch.bfloat16 if torch.cuda.is_available() else torch.float32

print(f"Loading Qwen3-TTS on device: {device} ({dtype})")

# 2. Load model & tokenizer
# Options: "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice" or "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign"
model_id = "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice"
model = Qwen3TTSModel.from_pretrained(
    model_id,
    torch_dtype=dtype,
    device_map=device
)

text = "Welcome to the audiobook generation pipeline using Qwen3-TTS. This produces expressive, natural speech."
output_path = "qwen_output.wav"

# 3. Generate audio samples
# Returns a dictionary or tuple with raw sample tensors and sampling rate
with torch.no_grad():
    output = model.generate_speech(
        text=text,
        voice="Vivian",  # Built-in voice or reference audio embedding
        language="en"
    )

# 4. Extract samples tensor and convert to NumPy array
# Output tensor shape is typically (channels, samples) or (samples,)
audio_tensor = output["audio"] if isinstance(output, dict) else output[0]
sample_rate = output["sample_rate"] if isinstance(output, dict) else output[1]

# Move tensor to CPU and convert to NumPy array
if isinstance(audio_tensor, torch.Tensor):
    audio_samples = audio_tensor.detach().cpu().numpy().squeeze()
else:
    audio_samples = np.array(audio_tensor).squeeze()

# 5. Normalize and save via SoundFile
max_val = np.max(np.abs(audio_samples))
if max_val > 0:
    normalized_samples = (audio_samples / max_val * 32767 * 0.95).astype(np.int16)
else:
    normalized_samples = audio_samples.astype(np.int16)

sf.write(output_path, normalized_samples, sample_rate)
print(f"Saved {len(normalized_samples) / sample_rate:.2f}s of audio to {output_path}")