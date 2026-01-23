# PDF to Audiobook Converter

Convert PDF books into high-quality audiobooks using Kokoro TTS. This tool extracts text from PDFs with intelligent chapter splitting based on the table of contents, cleans the text for optimal TTS output, and generates natural-sounding audio using local AI models.

## Features

- **PDF Text Extraction**: Extracts text with automatic header/footer removal
- **TOC-based Chapter Splitting**: Automatically splits content based on the PDF's table of contents
- **Text Cleaning Pipeline**: 
  - Fixes ligatures (fi, fl, ff, etc.)
  - Expands abbreviations (Mr., Dr., etc.)
  - Converts numbers to words for natural speech
  - Removes citations and artifacts
- **Local TTS with Kokoro**: High-quality text-to-speech running entirely on your machine
- **Multiple Voices**: Support for American and British English voices (male/female)
- **Apple Silicon Optimized**: Uses MPS acceleration on M-series Macs

## Requirements

- Python 3.10+
- macOS with Apple Silicon (M1/M2/M3) recommended for MPS acceleration
- 32GB RAM recommended for large books

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd pdf-to-audiobook

# Install dependencies with uv
uv sync

# Or with pip
pip install pymupdf soundfile numpy regex num2words beautifulsoup4 lxml kokoro torch
```

## Usage

### Full Conversion (PDF to Audiobook)

```bash
python cli.py convert pdfs/my-book.pdf --output output --voice af_heart
```

### Extract Text Only

```bash
python cli.py extract pdfs/my-book.pdf --output output
```

### List Available Voices

```bash
python cli.py voices
```

### Test TTS

```bash
python cli.py test --voice am_liam --output test.wav
```

## Available Voices

### American Female
- `af_heart` - Warm, friendly (recommended)
- `af_alloy`, `af_bella`, `af_jessica`, `af_nicole`, `af_nova`, `af_river`, `af_sarah`, `af_sky`

### American Male
- `am_adam`, `am_echo`, `am_eric`, `am_liam`, `am_michael`, `am_onyx`

### British Female
- `bf_alice`, `bf_emma`, `bf_isabella`, `bf_lily`

### British Male
- `bm_daniel`, `bm_fable`, `bm_george`, `bm_lewis`

## Output Structure

```
output/
└── book-name/
    ├── text/
    │   ├── 01_Chapter_1.txt
    │   ├── 02_Chapter_2.txt
    │   └── ...
    └── audio/
        ├── 01_Chapter_1.wav
        ├── 02_Chapter_2.wav
        └── ...
```

## Project Structure

```
pdf-to-audiobook/
├── cli.py                    # Command-line interface
├── src/
│   ├── pdf_extractor.py      # PDF text extraction
│   └── tts_generator.py      # Kokoro TTS generation
├── pdfs/                     # Input PDF files
└── output/                   # Generated text and audio
```

## Performance

On Apple Silicon M-series Macs with MPS acceleration:
- ~8x realtime speed for TTS generation
- 1 hour of audio generated in ~7.5 minutes

## License

MIT License

## Acknowledgments

- [Kokoro TTS](https://huggingface.co/hexgrad/Kokoro-82M) for the high-quality local TTS model
- [PyMuPDF](https://pymupdf.readthedocs.io/) for PDF text extraction
