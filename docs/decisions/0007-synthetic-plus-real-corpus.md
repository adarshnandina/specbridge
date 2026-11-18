# 0007 - Synthetic plus real corpus

## Context
Real datasheets are copyrighted, heterogeneous and unlabelled; synthetic ones allow exact ground
truth, revisions, discontinued parts and an injection attack, but may be easier than reality.

## Decision
51 deterministic synthetic PDFs (3 fictional vendors, 4 layout families, deliberate format variety:
decimal commas, en dashes, `...`/`…`/`to` ranges, header-unit tables, footnotes, missing optional
fields; 5 revisions; 1 prompt-injection datasheet; hand-crafted parts that make agent scenarios
well-defined) provide labelled evaluation. 9 real public datasheets (listed with sha256 in
`corpus/real/manifest.yaml`, downloaded locally, not redistributed) act as distractors and as a
small provisional extraction test; their labels were drafted by Claude and are
`verified_by_human: false`, and any metric on them is reported as provisional.

## Consequences
- Synthetic results are an upper bound on real-world difficulty (bias documented in LIMITATIONS).
- Only 9 (not 10-20) real datasheets could be obtained automatically; several vendor sites block downloads.
