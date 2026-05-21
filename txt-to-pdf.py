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
    stdin,
    stdout,
)
from textwrap import (
    TextWrapper,
)

# Hard-coded A4 paper size & portrait orientation for now
PAGE_WIDTH_MM: Final[float] = 210.0
PAGE_HEIGHT_MM: Final[float] = 297.0

# Millimetres per typographic point
FONT_POINT_MM: Final[float] = 0.3528

# Use the built-in Courier monospace font
FONT_FACE: Final[str] = "Courier"
FONT_HEIGHT_PT: Final[int] = 12
FONT_WIDTH_PT: Final[int] = 8

# TODO: Compute these from the font metrics, paper size, and margins
PAGE_COLUMNS: Final[int] = 74
PAGE_LINES: Final[int] = 70

text_wrapper: Final[TextWrapper] = TextWrapper(
    width=PAGE_COLUMNS,
    expand_tabs=False,
    replace_whitespace=False,
    break_long_words=False,
    break_on_hyphens=False,
)

# Here's a tentative outline of what the main program should do.

# Write the PDF header and whatever prologue is necessary.  Set the page dimensions and font face & size.
# Loop for each page:
#     Let the text to be written to the current page be an empty string.
#     If there was any overflow from the last paragraph on the last page, add it to the text to be written to the current page.
#     Loop as long as there's input remaining and the text to be written to the current page does not exceed the number of lines on a page:
#         Let the current paragraph be an empty string.
#         Loop unconditionally:
#             Attempt to read a line from standard input.
#             If we hit end-of-file, record the fact that there's no input remaining, and break out of the loop.
#             If we read an empty line (indicating the end of a paragraph), break out of the loop.
#             Add the line to the current paragraph and continue looping over input lines.
#         If the current paragraph is not empty:
#             Wrap the current paragraph.
#             Add the current paragraph to the text to be written to the current page.
#         Continue looping over input paragraphs.
#     If there is no text to be written to the current page (there was no overflow from the last page and no new paragraphs), there's no need to write a new page; break out of the loop.
#     If the number of lines in the current page exceeds the length of a page, truncate it, and save the overflow to be added to the start of the next page.
#     Create a new page in the PDF file and write all the text to it.
#     Continue looping over pages.
# After all pages have been written, write the PDF cross-reference table and footer.
