# n.b. in rocm on consumer rdna4 it is often necessary to
# export MIOPEN_FIND_MODE=2
# export TORCH_BLAS_PREFER_HIPBLASLT=0 
import onnxruntime as ort
from kokoro_onnx import Kokoro

model_path = "model.onnx"
voices_path = "voices-v1.0.bin"
providers = ort.get_available_providers()
session = ort.InferenceSession(model_path, providers=providers)
kokoro = Kokoro.from_session(session, voices_path=voices_path)

def get_sample_generator(text: str, voice: str = "af_nova") -> bool:
    return kokoro.create_stream(
        text,
        voice=voice,
        speed=1.0,
        lang="en-us"
    )

if False:
    from txtai.pipeline import TextToSpeech
    tts = TextToSpeech("NeuML/kokoro-fp16-onnx")
    def generate_audio(
        text: str,
        output_path: str,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> bool:
        """Generate audio from text and save to file."""
        if not text.strip():
            print("Warning: Empty text provided")
            return False

        text = text.replace("—", " - ").replace("–", " - ")
        text = text.replace("“", '"').replace("”", '"').replace("’", "'").replace("‘", "'")

        start_time = time.time()
        file_time = 0
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with sf.SoundFile(output_path, mode="x", samplerate=24000, channels=1) as f:
            for chunk, rate in tts(text, speaker="af_nova", stream=True):
                f.write(chunk)
                chunk_time = len(chunk)/rate
                file_time += chunk_time
                print(chunk_time, file_time, file_time/(time.time()-start_time))
        return True