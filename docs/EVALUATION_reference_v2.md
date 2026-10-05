# Phase 1 evaluation_reference_v2

Published 2026-10-03T04:55:55.847443+00:00. Protocol: reference_v2.
Complete evaluation and passing the quality gate are separate outcomes.

## Quality decision

**FAILED: 31/40 outputs pass.** The gate requires at least
32/40 overall and at least 8/10 in every category. Scores use the same fixed
rubric for identity, body/pose, garment transfer, background/lighting and artifacts.
Failed executions remain in the denominator: 0.

| Category | Passing outputs | Category threshold |
|---|---|---|
| shirt | 9/10 | Meets 8/10 |
| hoodie | 9/10 | Meets 8/10 |
| jacket | 9/10 | Meets 8/10 |
| coat | 4/10 | Below 8/10 |

Categories meeting their individual threshold:
shirt, hoodie, jacket.
Validated categories for this full workflow:
none; the full gate has not passed.
Do not replace poor outputs, select different seeds, or merge experiment results
into the original benchmark. A changed workflow requires its own complete gate.

## Runtime on the evaluated GPU

RTX 5060, 8,151 MiB reported device VRAM; exact environment and pinned hashes
are in [environment.json](../evaluation/environment.json). Model: GGUF Q4_K_M;
25 steps, CFG 1, Euler/simple, denoise 1, aspect-preserving 1024 pixel budget.

| Measurement | Count | Minimum seconds | Median seconds | Maximum seconds |
|---|---|---|---|---|
| Completed outputs with timing | 40 | 179.101 | 192.7765 | 210.228 |
| Matched warm second seeds | 20 | 179.101 | 182.433 | 186.795 |

Sampled total-device peak VRAM: 7534 MiB.
Five-second sampling can miss short peaks and includes other desktop GPU usage.
Model-unloaded cold runs have warm operating-system file caches; they are not
machine cold boots. Exact cold-run records and delivered image dimensions are
in the [summary](../evaluation/summary_reference_v2.json). Restarted second seeds are
excluded from the matched warm set.
Some runs overlapped local CPU segmentation investigation; these timings describe
the observed machine envelope, rather than an exclusive-machine speed comparison.

Recovered outputs with missing original history/timing/VRAM: 0.
Recovery verifies the PNG's embedded exact graph, source/uploaded bytes and output
hash; missing telemetry is never reconstructed and is excluded from metrics.

## Evidence and limits

- [Scores and per-output observations](../evaluation/SCORES_reference_v2.md).
- [Reviewed record manifest](../evaluation/reviewed_results_reference_v2.json).
- [Protocol and score anchors](../evaluation/PROTOCOL.md).
- [Inputs, rights and coverage](../evaluation/ASSETS.md).
- Local comparison gallery: `.local/evaluation_gallery_reference_v2.html`.

Only one AI reviewer compared source/reference/output images. This is an
engineering benchmark, not independent human approval, representative customer
accuracy, or physical sizing evidence. Five subjects and five reference garments
limit coverage; four subjects originate from upstream example imagery whose
synthetic status is unknown. Only visible garment details are graded.
Protected-region and multi-reference modes have no quality claim from this run.
The Qwen Image 2.1 model has separate research/evaluation terms; the application's
MIT license does not remove those restrictions.
