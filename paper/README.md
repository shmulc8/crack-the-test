# Manuscript

`main.tex` is a journal-style, self-contained account of the exact result and
its computational verification. It is intentionally conservative about
novelty and explicit about the remaining lack of a third-party decisive run.

Build locally:

```sh
cd paper
latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
```

Before submission:

1. Have a domain expert review the reduction and Proposition 4.
2. Re-run both decisive audit scripts from a clean tagged commit.
3. Push the reproducible artifact to the public GitHub repository and cite its
   full 40-character commit SHA.
4. Add the author's preferred affiliation, postal address, and contact email.
5. Adapt formatting and declarations to the selected journal's template.

The source is standard LaTeX and can be uploaded directly to Overleaf as the
`paper/` directory.
