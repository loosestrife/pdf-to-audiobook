"""
PDF to Audiobook CLI

Converts PDF books into audiobooks using Kokoro TTS.
"""

import os
import sys
import argparse
import time
from typing import List, Optional

from src.pdf_extractor import (
    extract_pdf_to_chapters,
    save_chapters_as_text,
    Chapter
)
from src.tts_generator import (
    generate_audiobook,
    get_available_voices
)


def main():
    parser = argparse.ArgumentParser(
        description="Convert PDF books to audiobooks using Kokoro TTS",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cli.py convert pdfs/my-book.pdf --output output/my-book
  python cli.py convert pdfs/my-book.pdf --voice am_liam
  python cli.py extract pdfs/my-book.pdf --output output/my-book/text
  python cli.py voices
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Convert command - full PDF to audiobook
    convert_parser = subparsers.add_parser('convert', help='Convert PDF to audiobook')
    convert_parser.add_argument('pdf_path', help='Path to PDF file')
    convert_parser.add_argument('--output', '-o', default='output',
                                help='Output directory (default: output)')
    convert_parser.add_argument('--voice', '-v', default='af_heart',
                                help='Voice to use (default: af_heart)')
    convert_parser.add_argument('--speed', '-s', type=float, default=1.0,
                                help='Speech speed (default: 1.0)')
    convert_parser.add_argument('--skip-existing', action='store_true',
                                help='Skip chapters with existing audio files')
    
    # Extract command - just extract text
    extract_parser = subparsers.add_parser('extract', help='Extract text from PDF')
    extract_parser.add_argument('pdf_path', help='Path to PDF file')
    extract_parser.add_argument('--output', '-o', default='output',
                                help='Output directory (default: output)')
    
    # Voices command - list available voices
    voices_parser = subparsers.add_parser('voices', help='List available voices')
    
    # Test command - test TTS with sample text
    test_parser = subparsers.add_parser('test', help='Test TTS with sample text')
    test_parser.add_argument('--voice', '-v', default='af_heart',
                             help='Voice to test')
    test_parser.add_argument('--output', '-o', default='output/test/sample.wav',
                             help='Output audio file')
    
    args = parser.parse_args()
    
    if args.command == 'voices':
        print("\nAvailable English voices:\n")
        for voice_id, description in get_available_voices().items():
            print(f"  {voice_id}: {description}")
        return
    
    elif args.command == 'test':
        test_text = """This is a test of the audiobook generation system.
The text-to-speech engine should convert this text into natural sounding speech.
We are testing with the Kokoro model."""
        
        
        os.makedirs(os.path.dirname(args.output), exist_ok=True)
        success = generator.generate_audio(test_text, args.output)
        
        if success:
            print(f"\nTest audio saved to: {args.output}")
        else:
            print("Failed to generate test audio")
            sys.exit(1)
        return
    
    elif args.command == 'extract':
        print(f"\nExtracting text from: {args.pdf_path}")
        
        chapters = extract_pdf_to_chapters(args.pdf_path)
        
        # Get book name from filename
        book_name = os.path.splitext(os.path.basename(args.pdf_path))[0]
        output_dir = os.path.join(args.output, book_name, 'text')
        
        saved_files = save_chapters_as_text(chapters, output_dir)
        
        print(f"\nExtracted {len(saved_files)} chapters to: {output_dir}")
        return
    
    elif args.command == 'convert':
        print(f"\nConverting PDF to audiobook: {args.pdf_path}")
        print(f"Voice: {args.voice}")
        print(f"Speed: {args.speed}")
        
        start_time = time.time()
        
        # Step 1: Extract text from PDF
        print("\n=== Step 1: Extracting text from PDF ===")
        chapters = extract_pdf_to_chapters(args.pdf_path)
        
        # Get book name from filename
        book_name = os.path.splitext(os.path.basename(args.pdf_path))[0]
        text_output_dir = os.path.join(args.output, book_name, 'text')
        audio_output_dir = os.path.join(args.output, book_name, 'audio')
        
        # Save text files
        saved_text_files = save_chapters_as_text(chapters, text_output_dir)
        
        # Step 2: Generate audio for each chapter
        print("\n=== Step 2: Generating audio from text ===")
        
        # Filter out existing if requested
        text_files_to_process = saved_text_files
        if args.skip_existing:
            filtered = []
            for text_file in saved_text_files:
                base_name = os.path.splitext(os.path.basename(text_file))[0]
                audio_file = os.path.join(audio_output_dir, f"{base_name}.wav")
                if not os.path.exists(audio_file):
                    filtered.append(text_file)
                else:
                    print(f"  Skipping (exists): {base_name}.wav")
            text_files_to_process = filtered
        
        if not text_files_to_process:
            print("No chapters to process.")
            return
        
        generated_audio = generate_audiobook(
            text_files_to_process,
            audio_output_dir,
            voice=args.voice,
            speed=args.speed
        )
        
        # Summary
        elapsed = time.time() - start_time
        print(f"\n=== Conversion Complete ===")
        print(f"Text files: {text_output_dir}")
        print(f"Audio files: {audio_output_dir}")
        print(f"Chapters processed: {len(generated_audio)}")
        print(f"Total time: {elapsed/60:.1f} minutes")
        return
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
