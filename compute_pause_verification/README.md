# Compute-pause verification — briefing deck

Self-contained technical map of public research on **verifiable AI slowdown / pause** (Claim A: no covert frontier training under low trust).

Not a product pitch. Diagrams + who/what/maturity/lineage for the main papers and posts (Wasil, Shavit, Rahman, joshc, Cankaya Plan A/B, zkLLM, VerInf, FlexHEG, Peigné).

## Read

- **[`notes.pdf`](notes.pdf)** — print-ready briefing
- **[`notes.html`](notes.html)** — same content; open locally (figures load from `figures/`)

## Rebuild

```bash
python3 build_notes.py
# then print HTML → PDF, e.g. Chrome headless:
# google-chrome --headless --disable-gpu --no-pdf-header-footer \
#   --print-to-pdf=notes.pdf "file://$(pwd)/notes.html"
```

Depends on: `svg_panels.py`, `figures/`.

## Scope

**In:** Claim A mechanisms and the public research lineage around them.  
**Out:** commercial TEE “AI Passport” products aimed at model-identity / confidential-cloud claims (B/C), except as contrast.

## Figure sources

Press / schematic images are attributed in captions (Meta AI RSC, NVIDIA Blog, SemiAnalysis board sketch, FlexHEG paper figures, etc.). Educational use; not redistributed as stock assets.

## License

Code/text in this folder: MIT (same as parent repo), unless a cited figure’s original license is stricter — then that source governs the image.
