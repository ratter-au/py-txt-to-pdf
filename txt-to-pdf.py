#!/usr/bin/env python3
"""Convert a plain text file into a bare‐bones PDF, such that the text extracted from the PDF matches the original as closely as possible.

The script reads from standard input and writes to standard output.  Use the shell to redirect those streams appropriately:

```
python3 txt-to-pdf.py < example.txt > example.pdf
```

The paper size is hard‐coded to A4 and the font is hard‐coded to 12‐point Courier (one of the 14 standard PDF fonts, so it doesn't need to be embedded in the document), with a 15 mm margin on each edge: this gives 70 columns and 63 lines per page.  Text will be re‐encoded using Windows code page 1252; characters outside this set will be replaced with a question mark in the PDF, and a warning will be printed to standard error.

"""

from typing import (
    Final,
)
from sys import (
    stderr,
    stdin,
    stdout,
)
from textwrap import (
    TextWrapper,
)

# Hard-coded A4 paper size & portrait orientation for now
PAGE_WIDTH_MM: Final[float] = 210.0
PAGE_HEIGHT_MM: Final[float] = 297.0
PAGE_MARGIN_MM: Final[float] = 15.0

# Use the built‐in Courier monospace font
FONT_FACE: Final[str] = "Courier"
FONT_HEIGHT_PT: Final[float] = 12.0
# Courier has a glyph width of 3/5 of the em‐square
FONT_WIDTH_PT: Final[float] = FONT_HEIGHT_PT * 0.6
# Single-spaced; close‐fitting but legible for Courier
LINE_HEIGHT_PT: Final[float] = FONT_HEIGHT_PT

# Typographic points per millimetre
FONT_PT_PER_MM: Final[float] = 72.0 / 25.4

# Page geometry in points
PAGE_WIDTH_PT: Final[float] = PAGE_WIDTH_MM * FONT_PT_PER_MM
PAGE_HEIGHT_PT: Final[float] = PAGE_HEIGHT_MM * FONT_PT_PER_MM
PAGE_MARGIN_PT: Final[float] = PAGE_MARGIN_MM * FONT_PT_PER_MM

# Capacity of the text box, in characters and lines
PAGE_COLUMNS: Final[int] = int((PAGE_WIDTH_PT - (2 * PAGE_MARGIN_PT)) / FONT_WIDTH_PT)
PAGE_LINES: Final[int] = int((PAGE_HEIGHT_PT - (2 * PAGE_MARGIN_PT)) / LINE_HEIGHT_PT)

text_wrapper: Final[TextWrapper] = TextWrapper(
    width=PAGE_COLUMNS,
    expand_tabs=False,
    replace_whitespace=False,
    drop_whitespace=False,
    break_long_words=False,
    break_on_hyphens=False,
)

def wrap_lines(text: str) -> list[str]:
    """Soft‐wrap each input line that exceeds the column width; pass shorter lines through verbatim.

    Tabs are expanded to eight‐column tab stops, since Courier has no tab glyph and rendering them as PDF escape sequences would just produce invisible characters.
    """
    lines: Final[list[str]] = []
    for line in text.splitlines():
        line = line.expandtabs(8)
        if len(line) <= PAGE_COLUMNS:
            lines.append(line)
        else:
            wrapped_lines: Final[list[str]] = text_wrapper.wrap(line)
            lines.extend(wrapped_lines if wrapped_lines else [""])
    return lines

def paginate(lines: list[str]) -> list[list[str]]:
    """Group lines into fixed‐height pages."""
    if not lines: return [[]]
    return [lines[i:i + PAGE_LINES] for i in range(0, len(lines), PAGE_LINES)]

def encode_pdf_string(s: str) -> bytes:
    """Encode a string as a PDF literal, with backslashes, parentheses, and non‐printables escaped.

    Characters are mapped to single bytes via `cp1252`, which matches PDF's `WinAnsiEncoding` closely enough to cover the typographic punctuation (em/en dashes, smart quotes, ellipsis, bullet, dagger, €, ™, …) on top of plain ASCII and Latin‐1.  Anything outside `cp1252` is replaced with `?`.
    """
    out: Final[bytearray] = bytearray(b"(")
    for b in s.encode("cp1252", errors="replace"):
        if b in (0x28, 0x29, 0x5C):  # parentheses, backslash
            out.append(0x5C) # precede with a backslash
            out.append(b)
        elif 0x20 <= b <= 0x7E: # all other single‐byte printables
            out.append(b)
        else:
            out.extend(f"\\{b:03o}".encode("ascii")) # backslash escape
    out.append(ord(")"))
    return bytes(out)

def create_page_content_stream(page_lines: list[str]) -> bytes:
    """Build the PDF content stream that lays out one page of text."""
    x0: Final[float] = PAGE_MARGIN_PT
    y0: Final[float] = PAGE_HEIGHT_PT - (PAGE_MARGIN_PT + FONT_HEIGHT_PT)
    out: Final[bytearray] = bytearray()
    out.extend(b"BT\n")
    out.extend(f"/F1 {FONT_HEIGHT_PT:g} Tf\n".encode("ascii"))
    out.extend(f"1 0 0 1 {x0:.3f} {y0:.3f} Tm\n".encode("ascii"))
    for i, line in enumerate(page_lines):
        if i > 0:
            out.extend(f"0 -{LINE_HEIGHT_PT:g} Td\n".encode("ascii"))
        if line:
            out.extend(encode_pdf_string(line))
            out.extend(b" Tj\n")
    out.extend(b"ET\n")
    return bytes(out)

def write_pdf(pages: list[list[str]]) -> None:
    """Assemble the PDF for the given pages and write it to `stdout`."""
    n_pages: Final[int] = len(pages)

    # Object numbering:
    # 1 = Catalog
    # 2 = Pages
    # 3 = Font
    # and for each page i (0‐indexed):
    # 2i+4 = Page
    # 2i+5 = Contents
    objects: Final[dict[int, bytes]] = {}
    objects[1] = b"<< /Type /Catalog /Pages 2 0 R >>"
    kids: Final[str] = " ".join(f"{(2 * i) + 4} 0 R" for i in range(n_pages))
    objects[2] = (
        f"<< /Type /Pages /Kids [{kids}] /Count {n_pages} "
        f"/MediaBox [0 0 {PAGE_WIDTH_PT:.3f} {PAGE_HEIGHT_PT:.3f}] "
        f"/Resources << /Font << /F1 3 0 R >> >> >>"
    ).encode("ascii")
    objects[3] = (
        f"<< /Type /Font /Subtype /Type1 /BaseFont /{FONT_FACE} "
        f"/Encoding /WinAnsiEncoding >>"
    ).encode("ascii")
    for (i, page) in enumerate(pages):
        page_num: Final[int] = (2 * i) + 4
        content_num: Final[int] = page_num + 1
        objects[page_num] = (
            f"<< /Type /Page /Parent 2 0 R /Contents {content_num} 0 R >>"
        ).encode("ascii")
        stream: Final[bytes] = create_page_content_stream(page)
        objects[content_num] = (
            f"<< /Length {len(stream)} >>\nstream\n".encode("ascii")
            + stream
            + b"endstream"
        )

    out = stdout.buffer
    pos: int = 0

    def emit(b: bytes) -> None:
        nonlocal pos
        out.write(b)
        pos += len(b)

    # PDF header
    emit(b"%PDF-1.4\n")
    # Comment with high‐bit bytes to flag the file as binary to anything sniffing it (traditional, but might not be strictly necessary)
    emit(b"%\xA0\xA0\xA0\xA0\n")

    # Objects
    offsets: Final[dict[int, int]] = {}
    for n in sorted(objects):
        offsets[n] = pos
        emit(f"{n} 0 obj\n".encode("ascii"))
        emit(objects[n])
        emit(b"\nendobj\n")

    # Cross‐reference table
    n_objects: Final[int] = max(objects)
    xref_pos: Final[int] = pos
    emit(b"xref\n")
    emit(f"0 {n_objects + 1}\n".encode("ascii"))
    emit(b"0000000000 65535 f \n")
    for n in range(1, n_objects + 1):
        emit(f"{offsets[n]:010d} 00000 n \n".encode("ascii"))

    # PDF trailer
    emit(b"trailer\n")
    emit(f"<< /Size {n_objects + 1} /Root 1 0 R >>\n".encode("ascii"))
    emit(b"startxref\n")
    emit(f"{xref_pos}\n".encode("ascii"))
    emit(b"%%EOF\n")


def main() -> None:
    text: Final[str] = stdin.read()
    lines: Final[list[str]] = wrap_lines(text)
    pages: Final[list[list[str]]] = paginate(lines)
    write_pdf(pages)

    # `encode_pdf_string()` replaces any character outside `cp1252` / `WinAnsiEncoding` with ‘?’.
    # Report a single summary line on `stderr` if any such substitutions happened.
    # TODO: Once we rewrite everything using generators, we'll need to accumulate a running total of unencodable characters, instead of iterating over the input a second time.
    unencodables: list[str] = []
    for ch in text:
        try:
            ch.encode("cp1252")
        except UnicodeEncodeError:
            unencodables.append(ch)
    if unencodables:
        distinct = sorted(set(unencodables))
        shown = distinct[:5]
        examples = ", ".join(f"{ch!r} (U+{ord(ch):04X})" for ch in shown)
        if len(distinct) > len(shown):
            examples += f", and {len(distinct) - len(shown)} more"
        print(
            f"txt-to-pdf.py: warning: {len(unencodables)} character(s) outside WinAnsiEncoding replaced with '?': {examples}",
            file=stderr,
        )

if __name__ == "__main__":
    main()
