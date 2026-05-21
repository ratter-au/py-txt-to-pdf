#!/usr/bin/env python3
"""Convert a plain text file into a bare‐bones PDF, such that the text extracted from the PDF matches the original as closely as possible.

The script reads from standard input and writes to standard output.  Use the shell to redirect those streams appropriately:

```
python3 txt-to-pdf.py < example.txt > example.pdf
```
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
MARGIN_MM: Final[float] = 15.0

# Millimetres per typographic point
FONT_MM_PER_PT: Final[float] = 25.4 / 72.0

# Use the built-in Courier monospace font (one of the 14 standard PDF fonts,
# so no font embedding is required).
FONT_FACE: Final[str] = "Courier"
FONT_HEIGHT_PT: Final[float] = 12.0
# Courier is a monospaced font with a glyph advance of 600/1000 of the em-square.
FONT_WIDTH_PT: Final[float] = FONT_HEIGHT_PT * 0.6
# Single-spaced; close-fitting but legible for Courier.
LINE_HEIGHT_PT: Final[float] = FONT_HEIGHT_PT

# Page geometry in points
PAGE_WIDTH_PT: Final[float] = PAGE_WIDTH_MM / FONT_MM_PER_PT
PAGE_HEIGHT_PT: Final[float] = PAGE_HEIGHT_MM / FONT_MM_PER_PT
MARGIN_PT: Final[float] = MARGIN_MM / FONT_MM_PER_PT

# Capacity of the text box, in characters and lines
PAGE_COLUMNS: Final[int] = int((PAGE_WIDTH_PT - 2 * MARGIN_PT) / FONT_WIDTH_PT)
PAGE_LINES: Final[int] = int((PAGE_HEIGHT_PT - 2 * MARGIN_PT) / LINE_HEIGHT_PT)

text_wrapper: Final[TextWrapper] = TextWrapper(
    width=PAGE_COLUMNS,
    expand_tabs=False,
    replace_whitespace=False,
    drop_whitespace=False,
    break_long_words=False,
    break_on_hyphens=False,
)


def wrap_lines(text: str) -> list[str]:
    """Soft-wrap each input line that exceeds the column width; pass shorter lines through verbatim.

    Tabs are expanded to eight-column tab stops, since Courier has no tab glyph and rendering them as PDF escape sequences would just produce invisible characters.
    """
    out: list[str] = []
    for line in text.splitlines():
        line = line.expandtabs(8)
        if len(line) <= PAGE_COLUMNS:
            out.append(line)
        else:
            wrapped = text_wrapper.wrap(line)
            out.extend(wrapped if wrapped else [""])
    return out


def paginate(lines: list[str]) -> list[list[str]]:
    """Group lines into fixed-height pages."""
    if not lines:
        return [[]]
    return [lines[i:i + PAGE_LINES] for i in range(0, len(lines), PAGE_LINES)]


def pdf_string(s: str) -> bytes:
    """Encode a string as a PDF literal: (…), with `\\`, `(`, `)` and non-printables escaped."""
    out = bytearray(b"(")
    for ch in s:
        cp = ord(ch)
        # Anything outside the single-byte range gets replaced; WinAnsiEncoding can't represent it.
        b = cp if cp <= 0xFF else ord("?")
        if b in (0x28, 0x29, 0x5C):  # ( ) \
            out.append(0x5C)
            out.append(b)
        elif 0x20 <= b <= 0x7E:
            out.append(b)
        else:
            out.extend(f"\\{b:03o}".encode("ascii"))
    out.append(ord(")"))
    return bytes(out)


def content_stream(page_lines: list[str]) -> bytes:
    """Build the PDF content stream that lays out one page of text."""
    x0 = MARGIN_PT
    y0 = PAGE_HEIGHT_PT - MARGIN_PT - FONT_HEIGHT_PT
    out = bytearray()
    out.extend(b"BT\n")
    out.extend(f"/F1 {FONT_HEIGHT_PT:g} Tf\n".encode("ascii"))
    out.extend(f"1 0 0 1 {x0:.3f} {y0:.3f} Tm\n".encode("ascii"))
    for i, line in enumerate(page_lines):
        if i > 0:
            out.extend(f"0 -{LINE_HEIGHT_PT:g} Td\n".encode("ascii"))
        if line:
            out.extend(pdf_string(line))
            out.extend(b" Tj\n")
    out.extend(b"ET\n")
    return bytes(out)


def write_pdf(pages: list[list[str]]) -> None:
    """Assemble the PDF for the given pages and write it to stdout."""
    n_pages = len(pages)

    # Object numbering: 1 = Catalog, 2 = Pages, 3 = Font, and for each page i
    # (0-indexed): 4+2i = Page, 5+2i = Contents.
    objects: dict[int, bytes] = {}
    objects[1] = b"<< /Type /Catalog /Pages 2 0 R >>"
    kids = " ".join(f"{4 + 2 * i} 0 R" for i in range(n_pages))
    objects[2] = (
        f"<< /Type /Pages /Kids [{kids}] /Count {n_pages} "
        f"/MediaBox [0 0 {PAGE_WIDTH_PT:.3f} {PAGE_HEIGHT_PT:.3f}] "
        f"/Resources << /Font << /F1 3 0 R >> >> >>"
    ).encode("ascii")
    objects[3] = (
        f"<< /Type /Font /Subtype /Type1 /BaseFont /{FONT_FACE} "
        f"/Encoding /WinAnsiEncoding >>"
    ).encode("ascii")
    for i, page in enumerate(pages):
        page_num = 4 + 2 * i
        content_num = 5 + 2 * i
        objects[page_num] = (
            f"<< /Type /Page /Parent 2 0 R /Contents {content_num} 0 R >>"
        ).encode("ascii")
        stream = content_stream(page)
        objects[content_num] = (
            f"<< /Length {len(stream)} >>\nstream\n".encode("ascii")
            + stream
            + b"endstream"
        )

    out = stdout.buffer
    pos = 0

    def emit(b: bytes) -> None:
        nonlocal pos
        out.write(b)
        pos += len(b)

    emit(b"%PDF-1.4\n")
    # Comment with high-bit bytes flags the file as binary to anything sniffing it.
    emit(b"%\xe2\xe3\xcf\xd3\n")

    offsets: dict[int, int] = {}
    for n in sorted(objects):
        offsets[n] = pos
        emit(f"{n} 0 obj\n".encode("ascii"))
        emit(objects[n])
        emit(b"\nendobj\n")

    n_objects = max(objects)
    xref_pos = pos
    emit(b"xref\n")
    emit(f"0 {n_objects + 1}\n".encode("ascii"))
    emit(b"0000000000 65535 f \n")
    for n in range(1, n_objects + 1):
        emit(f"{offsets[n]:010d} 00000 n \n".encode("ascii"))

    emit(b"trailer\n")
    emit(f"<< /Size {n_objects + 1} /Root 1 0 R >>\n".encode("ascii"))
    emit(b"startxref\n")
    emit(f"{xref_pos}\n".encode("ascii"))
    emit(b"%%EOF\n")


def main() -> None:
    text = stdin.read()
    lines = wrap_lines(text)
    pages = paginate(lines)
    write_pdf(pages)

    # Codepoints above 0xFF can't be encoded in a single byte under WinAnsiEncoding;
    # pdf_string substitutes '?' for these.  Report a single summary line on stderr.
    unencodable = [ch for ch in text if ord(ch) > 0xFF]
    if unencodable:
        distinct = sorted(set(unencodable))
        shown = distinct[:5]
        examples = ", ".join(f"{ch!r} (U+{ord(ch):04X})" for ch in shown)
        if len(distinct) > len(shown):
            examples += f", and {len(distinct) - len(shown)} more"
        print(
            f"txt-to-pdf.py: warning: {len(unencodable)} non-Latin-1 "
            f"character(s) replaced with '?': {examples}",
            file=stderr,
        )


if __name__ == "__main__":
    main()
