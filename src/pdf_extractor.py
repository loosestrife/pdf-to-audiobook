"""
PDF Text Extraction Module

Extracts text from PDFs with TOC-based chapter splitting, 
header/footer removal, and text cleaning for TTS.
"""

import fitz  # PyMuPDF
import regex as re
import os
import unicodedata
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from num2words import num2words


# Configuration
HEADER_THRESHOLD = 50  # Pixels from top to ignore
FOOTER_THRESHOLD = 50  # Pixels from bottom to ignore


@dataclass
class Chapter:
    """Represents an extracted chapter."""
    number: int
    title: str
    text: str
    level: int = 1
    start_page: int = 0
    end_page: int = 0


def normalize_text(text: str) -> str:
    """Apply Unicode normalization and fix common problematic characters."""
    text = unicodedata.normalize('NFKC', text)
    text = text.replace('—', ', ')
    text = text.replace('–', ', ')
    text = text.replace('«', '"').replace('»', '"')
    text = text.replace(chr(8216), "'").replace(chr(8217), "'")
    text = text.replace(chr(8220), '"').replace(chr(8221), '"')
    # Fix ligatures that may cause TTS issues
    text = text.replace('ﬁ', 'fi')
    text = text.replace('ﬂ', 'fl')
    text = text.replace('ﬀ', 'ff')
    text = text.replace('ﬃ', 'ffi')
    text = text.replace('ﬄ', 'ffl')
    # Fix broken ligatures with space (e.g., "fi " -> "fi")
    text = text.replace('fi ', 'fi')
    text = text.replace('fl ', 'fl')
    return text


def expand_abbreviations(text: str) -> str:
    """Expand common abbreviations for TTS."""
    abbreviations = {
        r'\bMr\.': 'Mister',
        r'\bMrs\.': 'Misses',
        r'\bMs\.': 'Miss',
        r'\bDr\.': 'Doctor',
        r'\bProf\.': 'Professor',
        r'\bJr\.': 'Junior',
        r'\bSr\.': 'Senior',
        r'\bvs\.': 'versus',
        r'\betc\.': 'etcetera',
        r'\bi\.e\.': 'that is',
        r'\be\.g\.': 'for example',
        r'\bcf\.': 'compare',
        r'\bVol\.': 'Volume',
        r'\bNo\.': 'Number',
        r'\bpp\.': 'pages',
        r'\bp\.': 'page',
        r'\bet al\.': 'and others',
    }
    for abbr, expansion in abbreviations.items():
        text = re.sub(abbr, expansion, text, flags=re.IGNORECASE)
    
    # Fix initials like "E. B. White" -> "E B White"
    text = re.sub(r'([A-Z])\.(?=\s*[A-Z])', r'\1', text)
    text = re.sub(r' +', ' ', text)
    return text


def convert_numbers_to_words(text: str) -> str:
    """Convert numbers to words for better TTS."""
    # Remove comma thousand separators
    text = re.sub(r'(?<=\d),(?=\d)', '', text)
    
    def replace_match(match):
        num_str = match.group(1)
        suffix = match.group(2)
        try:
            if '.' in num_str:
                return match.group(0)
            num = int(num_str)
            if 1500 <= num <= 2100:
                return num2words(num, to='year')
            elif suffix:
                return num2words(num, to='ordinal')
            elif num < 10000:
                return num2words(num)
            else:
                return num_str
        except (ValueError, KeyError):
            return match.group(0)
    
    pattern = r'\b(\d+)(st|nd|rd|th)?\b'
    text = re.sub(pattern, replace_match, text)
    return text


def remove_artifacts(text: str) -> str:
    """Remove common extraction artifacts."""
    # Remove bracketed numbers (citations, footnotes)
    text = re.sub(r'\[\s*\d+\s*\]', '', text)
    # Remove standalone page numbers
    text = re.sub(r'^\s*\d+\s*$', '', text, flags=re.MULTILINE)
    # Remove lines that are just punctuation
    text = re.sub(r'^\s*[.,;:!?\-—–_]+\s*$', '', text, flags=re.MULTILINE)
    # Collapse multiple blank lines
    text = re.sub(r'\n\s*\n+', '\n\n', text)
    return text.strip()


def join_wrapped_lines(text: str) -> str:
    """Join lines that seem to be wrapped mid-sentence."""
    lines = text.splitlines()
    if not lines:
        return ""
    
    result_lines = []
    buffer = lines[0]
    
    for i in range(1, len(lines)):
        current_line = lines[i].strip()
        prev_line_stripped = buffer.strip()
        
        # Join if previous doesn't end with sentence punctuation
        # and current doesn't start like a new paragraph
        if (prev_line_stripped and
            not re.search(r'[.!?:)"\'\u00BB]$', prev_line_stripped) and
            current_line and
            not re.match(r'^[A-Z\d"\u00AB\'\[\*\-\u2022]', current_line) and
            len(prev_line_stripped.split()) > 1):
            buffer += " " + current_line
        else:
            if buffer.strip():
                result_lines.append(buffer.strip())
            buffer = current_line
    
    if buffer.strip():
        result_lines.append(buffer.strip())
    
    return '\n'.join(result_lines)


def clean_text_for_tts(text: str) -> str:
    """Apply the full text cleaning pipeline."""
    if not text:
        return ""
    
    text = normalize_text(text)
    text = join_wrapped_lines(text)
    text = expand_abbreviations(text)
    text = convert_numbers_to_words(text)
    text = remove_artifacts(text)
    
    # Final whitespace cleanup
    text = re.sub(r' +', ' ', text)
    text = re.sub(r'\n\n+', '\n\n', text)
    
    return text.strip()


def extract_page_text(page: fitz.Page) -> str:
    """Extract text from a single page, filtering headers/footers."""
    page_height = page.rect.height
    blocks = page.get_text("blocks", flags=fitz.TEXTFLAGS_TEXT)
    
    filtered_lines = []
    for block in blocks:
        x0, y0, x1, y1, text, *_ = block
        # Skip headers and footers
        if y1 < HEADER_THRESHOLD or y0 > page_height - FOOTER_THRESHOLD:
            continue
        
        cleaned_block = re.sub(r'\s+', ' ', text).strip()
        if cleaned_block:
            filtered_lines.append(cleaned_block)
    
    return "\n".join(filtered_lines)


def get_toc(doc: fitz.Document) -> List[Tuple[int, str, int]]:
    """Extract and validate TOC from PDF."""
    toc = doc.get_toc()
    if not toc:
        return []
    
    # Deduplicate by page number
    seen_pages = set()
    deduplicated = []
    for entry in toc:
        level, title, page_num = entry
        if page_num not in seen_pages:
            deduplicated.append(entry)
            seen_pages.add(page_num)
    
    return deduplicated


def extract_chapters_by_toc(doc: fitz.Document, toc: List[Tuple[int, str, int]]) -> List[Chapter]:
    """Extract chapters based on TOC structure."""
    chapters = []
    num_pages = len(doc)
    
    # Extract all page text upfront
    all_pages_text = []
    for page_num in range(num_pages):
        page = doc.load_page(page_num)
        all_pages_text.append(extract_page_text(page))
    
    for i, entry in enumerate(toc):
        level, title, start_page = entry
        start_idx = start_page - 1  # 0-based
        
        # Determine end page
        if i < len(toc) - 1:
            _, _, next_start = toc[i + 1]
            end_idx = next_start - 2
        else:
            end_idx = num_pages - 1
        
        # Validate indices
        if start_idx < 0 or start_idx >= num_pages:
            continue
        end_idx = max(start_idx, min(end_idx, num_pages - 1))
        
        # Extract and clean text
        chapter_pages = all_pages_text[start_idx:end_idx + 1]
        raw_text = "\n".join(chapter_pages)
        cleaned_text = clean_text_for_tts(raw_text)
        
        # Clean title
        clean_title = title.strip()
        clean_title = re.sub(r'\s+', ' ', clean_title)
        
        if cleaned_text:
            chapters.append(Chapter(
                number=i + 1,
                title=clean_title,
                text=cleaned_text,
                level=level,
                start_page=start_page,
                end_page=end_idx + 1
            ))
    
    return chapters


def should_include_chapter(chapter: Chapter) -> bool:
    """Determine if a chapter should be included in the audiobook."""
    # Skip front matter and back matter that isn't content
    skip_titles = [
        'cover', 'half title', 'title page', 'copyright',
        'dedication', 'table of contents', 'bibliography',
        'index', 'references', 'notes', 'about the author'
    ]
    title_lower = chapter.title.lower()
    
    for skip in skip_titles:
        if skip in title_lower:
            return False
    
    # Also skip very short chapters (likely front matter)
    if len(chapter.text) < 500:
        return False
    
    return True


def extract_pdf_to_chapters(pdf_path: str) -> List[Chapter]:
    """Main function to extract PDF content into chapters."""
    print(f"Opening PDF: {pdf_path}")
    doc = fitz.open(pdf_path)
    
    print(f"Total pages: {len(doc)}")
    
    # Get TOC
    toc = get_toc(doc)
    print(f"TOC entries found: {len(toc)}")
    
    if not toc:
        raise ValueError("PDF has no Table of Contents. Cannot split into chapters.")
    
    # Extract chapters
    chapters = extract_chapters_by_toc(doc, toc)
    print(f"Extracted {len(chapters)} chapters")
    
    # Filter to content chapters only
    content_chapters = [ch for ch in chapters if should_include_chapter(ch)]
    print(f"Content chapters (excluding front/back matter): {len(content_chapters)}")
    
    doc.close()
    return content_chapters


def chapters_to_markdown(chapters: List[Chapter], book_title: str = "Book") -> str:
    """Convert chapters to markdown format."""
    lines = [f"# {book_title}", ""]
    
    for chapter in chapters:
        # Determine header level based on TOC level
        header = "#" * (chapter.level + 1)
        lines.append(f"{header} {chapter.title}")
        lines.append("")
        lines.append(chapter.text)
        lines.append("")
        lines.append("---")
        lines.append("")
    
    return "\n".join(lines)


def save_chapters_as_text(chapters: List[Chapter], output_dir: str) -> List[str]:
    """Save each chapter as a separate text file."""
    os.makedirs(output_dir, exist_ok=True)
    saved_files = []
    
    padding = len(str(len(chapters)))
    
    for chapter in chapters:
        # Create safe filename
        safe_title = re.sub(r'[^\w\s-]', '', chapter.title).strip()
        safe_title = re.sub(r'\s+', '_', safe_title)[:60]
        if not safe_title:
            safe_title = f"chapter_{chapter.number}"
        
        filename = f"{str(chapter.number).zfill(padding)}_{safe_title}.txt"
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(chapter.text)
        
        saved_files.append(filepath)
        print(f"  Saved: {filename}")
    
    return saved_files


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python pdf_extractor.py <pdf_path>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    chapters = extract_pdf_to_chapters(pdf_path)
    
    for ch in chapters[:5]:
        print(f"\n=== {ch.title} (pages {ch.start_page}-{ch.end_page}) ===")
        print(ch.text[:500] + "...")
