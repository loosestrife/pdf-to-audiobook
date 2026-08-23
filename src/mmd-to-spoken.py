import sys
import re
from pathlib import Path
import ollama

SYSTEM_PROMPT = """You are an expert mathematics professor narrating an advanced textbook for an audio recording.
Your goal is to convey the structural intuition of dense mathematical expressions without causing cognitive overload for a listener who cannot see the page.

Instructions:
1. STATE THE SCAFFOLD FIRST: Describe the top-level operator or global structure before filling in the details.
2. DECONSTRUCT THE COMPONENTS: Walk through the major terms left-to-right or inner-to-outer, explaining the physical or structural role of each piece.
3. AVOID RAW SYNTAX: Never say "backslash", "open brace", "subscript", or "caret". Convert indices and bounds to spoken relations.
4. KEEP IT CONTINUOUS: Output pure, fluid English prose with natural punctuation so the neural TTS engine can infer correct cadence and pauses.
5. NO META TEXT: Do not include introductory phrases like "Here is the narrated text". Output only the spoken script."""

MODEL_NAME = "qwen3.8:27b"  # Adjust tag to match your exact local Ollama model

def process_section(section_text: str) -> str:
    """Sends a single markdown chunk to Qwen."""
    if not section_text.strip():
        return ""
    
    response = ollama.generate(
        model=MODEL_NAME,
        system=SYSTEM_PROMPT,
        prompt=section_text,
        options={
            "temperature": 0.3,  # Lower temp keeps mathematical translations precise
        }
    )
    return response['response']

def mmd_to_spoken_text(input_mmd_path: str, output_txt_path: str):
    mmd_path = Path(input_mmd_path)
    txt_path = Path(output_txt_path)
    
    print(f"Reading {mmd_path}...")
    content = mmd_path.read_text(encoding="utf-8")
    
    # Split content by major sections or double newlines to avoid exceeding generation output limits
    sections = re.split(r'\n(?=#{1,3}\s)', content)
    
    spoken_sections = []
    print(f"Processing {len(sections)} sections through {MODEL_NAME}...")
    
    for i, section in enumerate(sections, 1):
        print(f"  [+] Translating section {i}/{len(sections)}...")
        spoken_text = process_section(section)
        spoken_sections.append(spoken_text.strip())
    
    final_spoken_doc = "\n\n".join(spoken_sections)
    
    # Final cleanup pass for stray characters that confuse Kokoro
    final_spoken_doc = re.sub(r'[\*\_`\#\$]', '', final_spoken_doc)
    
    txt_path.write_text(final_spoken_doc, encoding="utf-8")
    print(f"Done! Written to {txt_path}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python mmd_to_spoken.py <input.mmd> <output.txt>")
        sys.exit(1)
        
    mmd_to_spoken_text(sys.argv[1], sys.argv[2])
