# Manuscript TeX Draft

Main file:

```text
main.tex
```

Compile from this directory so relative figure paths resolve:

```powershell
cd manuscript
pdflatex main.tex
pdflatex main.tex
```

The draft inserts key figures from `../outputs/figures/` and core result tables
from the current Phase 4-7 outputs. It is an outline-plus-results scaffold, not
yet a polished submission manuscript.
