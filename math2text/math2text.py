import chonkie
import ollama
import re
import time
from pathlib import Path

SYSTEM_PROMPT = """You are an expert mathematics professor narrating an advanced textbook for an audio recording.
Your goal is to convey the structural intuition of dense mathematical expressions without causing cognitive overload for a listener who cannot see the page.

Instructions:
1. STATE THE SCAFFOLD FIRST: Describe the top-level operator or global structure before filling in the details.
2. DECONSTRUCT THE COMPONENTS: Walk through the major terms left-to-right or inner-to-outer, explaining the physical or structural role of each piece.
3. AVOID RAW SYNTAX: Never say "backslash", "open brace", "subscript", or "caret". Convert indices and bounds to spoken relations.
4. KEEP IT CONTINUOUS: Output pure, fluid English prose with natural punctuation so the neural TTS engine can infer correct cadence and pauses.
5. NO META TEXT: Do not include introductory phrases like "Here is the narrated text". Output only the spoken script."""

SYSTEM_PROMPT = """You are an expert mathematics professor narrating an advanced textbook for an audio recording.  Your goal is to convey the structural intuition of dense mathematical expressions without causing cognitive overload for a listener who cannot see the page.

Instructions:
1. STATE THE SCAFFOLD FIRST: Name the core mathematical object and the global structure first before filling in details.  Introduce bounds, limits, or indices afterward to avoid cognitive overload.
2. DECONSTRUCT THE COMPONENTS: Walk through the major terms, explaining the physical or structural role of each piece.
3. MINIMIZE SYMBOL INTRODUCTIONS: Introduce as few symbols per sentence as possible. Unpack complex indices or multi-term expressions into separate, bite-sized conceptual thoughts.
4. SPOKEN WORDS NOT LATEX: Speak like a mathematician explaining an equation at a whiteboard to a blind colleague.
5. KEEP IT CONTINUOUS: Output pure, fluid English prose with natural punctuation, the way a mathematician would say it out loud.
"""

MODEL_NAME = "qwen3.8:27b"
#MODEL_NAME = "smtek/Qwen3.8-27B:Q3_K_XL-16gb"
#MODEL_NAME = "hf.co/QuantFactory/Qwen2.5-Math-14B-Instruct-GGUF:Q5_K_M"
#MODEL_NAME = "ornith-1.5:9b"
#MODEL_NAME = "gemma4:12b"
#MODEL_NAME = "hf.co/logic65/Qwen3.8-Whittle-tri-14.7B"
#MODEL_NAME = "hf.co/unsloth/Qwen3.8-27B-GGUF:UD-Q3_K_XL"

client = ollama.Client()
def process_section(section_text: str) -> str:
    """Sends a single markdown chunk to Qwen."""
    if not section_text.strip():
        return ""
    
    response = ollama.generate(
        model=MODEL_NAME,
        system=SYSTEM_PROMPT,
        prompt=section_text,
        keep_alive=10,
        options={
            "temperature": 0.1,
        }
    )
    return response['response']

def format_time(seconds: float) -> str:
    """Formats seconds into MM:SS or HH:MM:SS string."""
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h:02d}h{m:02d}m{s:02d}s"
    return f"{m:02d}m{s:02d}s"



def math2text(content: str):
    paras = content.split('\n\n')
    stride = 3
    chunks = ['\n'.join(paras[i : i + stride]) for i in range(0, len(paras), stride)]
    spoken_sections = []
    start_time = time.time()
    processed_chars = 0
    total_chars = len(content)
    print(f"Processing {len(chunks)} chunks through {MODEL_NAME}...")
    for i, chunk in enumerate(chunks, 1):
        istr = f"{i:04d}"
        chunkDir = "text-chunks"
        chunkOutPath = f"{chunkDir}/chunk{istr}.txt"
        textOutPath = f"{chunkDir}/text{istr}.txt"
        if Path(textOutPath).exists():
            continue
        print(f"  [+] Translating section {i}/{len(chunks)}...")
        chunk_start = time.time()
        spoken_text = process_section(chunk)

        chunk_elapsed = time.time() - chunk_start
        total_elapsed = time.time() - start_time
        chunk_cps = len(chunk) / chunk_elapsed
        processed_chars += len(chunk)
        total_cps = processed_chars / total_elapsed if total_elapsed > 0 else 0
        remaining_chars = total_chars - processed_chars
        eta_seconds = remaining_chars / total_cps if total_cps > 0 else 0
        print(f"{total_cps:.1f} char/s eta {format_time(eta_seconds)} (chunk  {chunk_cps:.1f} chars/s {format_time(chunk_elapsed)})\n")
        print(spoken_text)

        spoken_sections.append(spoken_text.strip())
        Path(chunkOutPath).write_text(chunk)
        Path(textOutPath).write_text(spoken_text)



    final_spoken_doc = "\n\n".join(spoken_sections)
    final_spoken_doc = re.sub(r'[\*\_`\#\$]', '', final_spoken_doc)
    return final_spoken_doc   

