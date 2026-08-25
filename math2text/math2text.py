import ollama

SYSTEM_PROMPT = """You are an expert mathematics professor narrating an advanced textbook for an audio recording.
Your goal is to convey the structural intuition of dense mathematical expressions without causing cognitive overload for a listener who cannot see the page.

Instructions:
1. STATE THE SCAFFOLD FIRST: Describe the top-level operator or global structure before filling in the details.
2. DECONSTRUCT THE COMPONENTS: Walk through the major terms left-to-right or inner-to-outer, explaining the physical or structural role of each piece.
3. AVOID RAW SYNTAX: Never say "backslash", "open brace", "subscript", or "caret". Convert indices and bounds to spoken relations.
4. KEEP IT CONTINUOUS: Output pure, fluid English prose with natural punctuation so the neural TTS engine can infer correct cadence and pauses.
5. NO META TEXT: Do not include introductory phrases like "Here is the narrated text". Output only the spoken script."""

MODEL_NAME = "qwen3.8:27b"

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

def math2text(input_mmd_path: str, output_txt_path: str):
    sections = re.split(r'\n(?=#{1,3}\s)', content)
    spoken_sections = []
    print(f"Processing {len(sections)} sections through {MODEL_NAME}...")
    for i, section in enumerate(sections, 1):
        print(f"  [+] Translating section {i}/{len(sections)}...")
        spoken_text = process_section(section)
        spoken_sections.append(spoken_text.strip())
    final_spoken_doc = "\n\n".join(spoken_sections)
    final_spoken_doc = re.sub(r'[\*\_`\#\$]', '', final_spoken_doc)
    return final_spoken_doc   
