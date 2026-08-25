import asyncio
from collections import defaultdict
from chonkie import SemanticChunker
import numpy as np
import os
import soundfile as sf
import time

from .conf import conf
from .tts import TTS_REGISTRY

def main():
    with open(conf.infile, "r", encoding="utf-8") as f:
        text = f.read().strip()
    engine_cls = TTS_REGISTRY[conf.tts]
    engine = engine_cls()
    generate_audiofile(engine, text, conf.outfile)


chunk_size = defaultdict(lambda: 300, {
    'kokoro': 150,
    'qwen3': 300,
    'piper': 180
})

def generate_audiofile(engine, text: str, output_path: str) -> bool:
    if not text.strip():
        return False
    text_chunks = []
    if conf.chunker == "chonkie":
        chunker = SemanticChunker(
            embedding_model="minishlab/potion-base-32M",
            chunk_size=chunk_size[conf.tts] * (.3 if conf.math else 1),
            threshold=0.68
        )
        text_chunks = chunker.chunk(text)
        print(f"Chunked {len(text)} chars into {len(text_chunks)} chunks")
        
    else:
        text_chunks = [{'text': text}]

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    if conf.chunker == "none" and hasattr(engine, 'get_sample_generator'):
        generator = engine.get_sample_generator(text)
        async def _stream_to_file():
            total_time = 0.0
            start_time = time.time()
            audio_chunks = []
            async for samples, sample_rate in generator:
                if samples is not None and len(samples) > 0:
                    chunk_time = len(samples) / sample_rate
                    total_time += chunk_time
                    print(total_time, '(', chunk_time, ')', total_time/(time.time()-start_time))
                    audio_chunks.append(normalize(samples))
            with sf.SoundFile(output_path, mode="w", samplerate=conf.rate, channels=1) as f:
                for audio_chunk in audio_chunks:
                    f.write(audio_chunk)
        asyncio.run(_stream_to_file())
    else:
        cur_chars = 0
        cur_time = 0
        start_time = time.time()
        finish_chars = len(text)
        chars_width = len(str(finish_chars))
        audio_chunks = []
        stride = 16
        for text_chunk_chunk in [text_chunks[i : i + stride] for i in range(0, len(text_chunks), stride)]:
            text_str_chunk = [text_chunk.text for text_chunk in text_chunk_chunk]
            samples, sample_rate = engine.generate_samples(text_str_chunk)
            audio_chunks.append(samples)

            chunk_chars = sum([len(text_str) for text_str in text_str_chunk])
            chunk_time = len(samples) / sample_rate
            cur_chars += chunk_chars
            cur_time += chunk_time
            elapsed_time = time.time() - start_time
            rtf = cur_time / elapsed_time if elapsed_time > 0 else 0.0
            char_speed = cur_chars / elapsed_time if elapsed_time > 0 else 0.0
            remaining_chars = finish_chars - cur_chars
            eta_seconds = remaining_chars / char_speed if char_speed > 0 else 0.0
            pct = (cur_chars / finish_chars) * 100
            print(
                f"[{cur_chars:>6d}/{finish_chars}] ({pct:>5.1f}%) | "
                f"{rtf:>4.1f}xRTF ({char_speed:>4.1f} char/s) | "
                f"Audio: {format_time(cur_time)}({format_time(elapsed_time)}) | "
                f"ETA: {format_time(eta_seconds)}"
            )
        sf.write(conf.outfile, np.concatenate(audio_chunks), conf.rate)

def format_time(seconds: float) -> str:
    """Formats seconds into MM:SS or HH:MM:SS string."""
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h:02d}h{m:02d}m{s:02d}s"
    return f"{m:02d}m{s:02d}s"

def normalize(samples):
    max_val = np.max(np.abs(samples))
    if max_val > 0:
        return (samples / max_val * 32767 * 0.95).astype(np.int16)
    else:
        return samples.astype(np.int16)

if __name__ == "__main__":
    main()
