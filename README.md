# `ratter-au/py-txt-to-pdf`

Convert a plain text file into a bare‐bones PDF, such that the text extracted from the PDF matches the original as closely as possible.

Characters outside [Windows code page 1252](https://en.wikipedia.org/wiki/Windows-1252) will be replaced in the output with a question mark.

**This is a work in progress.**  Claude wrote most of the code and I haven't yet checked it exhaustively.  It appears to do its job as far as I'm able to tell via quick manual testing.

## Usage

The script reads from standard input and writes to standard output.  Use the shell to redirect those streams appropriately:

```
python3 txt-to-pdf.py < example.txt > example.pdf
```

## To do

- Tests!
- Rewrite some of Claude's code to suit my own style.

## License

The contents of this repository are released under
[the Creative Commons Attribution 4.0 International (CC-BY-4.0) license](./LICENSE.txt).
