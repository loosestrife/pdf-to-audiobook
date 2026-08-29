import argparse
from pathlib import Path
from chonkie import SentenceChunker
from .math2text import math2text

parser = argparse.ArgumentParser(
    description="Convert MathML/LaTeX documents to spoken text files for TTS."
)
parser.add_argument("input_mmd", type=Path, help="Path to input .mmd file")
parser.add_argument("output_txt", type=Path, help="Path to output .txt file")
parser.add_argument(
    "--num-chunks",
    type=int,
    default=1,
    help="Number of chunks to split output into for Snakemake parallelization.",
)
args = parser.parse_args()

def split_text_into_chunks(text: str, num_chunks: int) -> list[str]:
    """Splits text into N balanced parts without breaking sentences."""
    if num_chunks <= 1:
        return [text]

    chunker = SentenceChunker(chunk_size=500)
    sentence_chunks = chunker.chunk(text)

    total_chars = len(text)
    target_chars = total_chars / num_chunks

    parts = [[] for _ in range(num_chunks)]
    part_lengths = [0] * num_chunks
    curr_part = 0

    for sentence in sentence_chunks:
        sentence_str = sentence.text if hasattr(sentence, "text") else str(sentence)
        if (part_lengths[curr_part] + len(sentence_str) > target_chars) and (curr_part < num_chunks - 1):
            curr_part += 1

        parts[curr_part].append(sentence_str)
        part_lengths[curr_part] += len(sentence_str)

    return [" ".join(p) for p in parts]


def main():
    print(f"Reading {args.input_mmd}...")
    in_text = args.input_mmd.read_text(encoding="utf-8")
    spoken_text = math2text(in_text)

    out_chunks = split_text_into_chunks(spoken_text, args.num_chunks)

    if args.num_chunks == 1:
        args.output_txt.parent.mkdir(parents=True, exist_ok=True)
        args.output_txt.write_text(spoken_text, encoding="utf-8")
        print(f"Done! Written to {args.output_txt}")
    else:
        stem = args.output_txt.stem
        ext = args.output_txt.suffix
        parent = args.output_txt.parent
        parent.mkdir(parents=True, exist_ok=True)

        for idx, chunk_str in enumerate(out_chunks):
            chunk_file = parent / f"{stem}_part_{idx:02d}{ext}"
            chunk_file.write_text(chunk_str, encoding="utf-8")
            print(f"Done! Chunk {idx:02d} written to {chunk_file}")

if __name__ == "__main__":
    main()