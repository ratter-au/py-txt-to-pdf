# `ratter-au/py-txt-to-pdf`

Convert a plain text file into a bare‐bones PDF, such that the text extracted from the PDF matches the original as closely as possible.

The paper size is hard‐coded to A4 and the font is hard‐coded to 12‐point Courier (one of the standard PDF fonts), with a 15 mm margin on each edge: this gives 70 columns and 63 lines per page.

Text will be re‐encoded using [Windows code page 1252](https://en.wikipedia.org/wiki/Windows-1252); characters outside this set will be replaced with a question mark in the PDF, and a warning will be printed to standard error.

**This is a work in progress.**  Claude wrote most of the code and I haven't yet tested it exhaustively.  It appears to do its job as far as I'm able to tell via quick manual testing.

## Usage

The script reads from standard input and writes to standard output.  Use the shell to redirect those streams appropriately:

```
python3 txt-to-pdf.py < example.txt > example.pdf
```

## To do

- Tests!
- Rewrite using generators, with streaming input & output, instead of reading everything all at once.

## License

The contents of this repository are released under
[the Creative Commons Attribution 4.0 International (CC-BY-4.0) license](./LICENSE.txt).
