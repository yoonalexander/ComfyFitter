# Phase 1 evaluation_category_reference_v4

Published 2026-10-03T16:04:52.240924+00:00. Protocol: category_reference_v4.
Complete evaluation and passing the quality gate are separate outcomes.

## Quality decision

**PASSED: 36/40 outputs pass.** The gate requires at least
32/40 overall and at least 8/10 in every category. Scores use the same fixed
rubric for identity, body/pose, garment transfer, background/lighting and artifacts.
Failed executions remain in the denominator: 0.

| Category | Passing outputs | Category threshold |
|---|---|---|
| shirt | 9/10 | Meets 8/10 |
| hoodie | 9/10 | Meets 8/10 |
| jacket | 9/10 | Meets 8/10 |
| coat | 9/10 | Meets 8/10 |

Categories meeting their individual threshold:
shirt, hoodie, jacket, coat.
Validated categories for this full workflow:
shirt, hoodie, jacket, coat.
Do not replace poor outputs, select different seeds, or merge experiment results
into the original benchmark. A changed workflow requires its own complete gate.

## Runtime on the evaluated GPU

RTX 5060, 8,151 MiB reported device VRAM; exact environment and pinned hashes
are in [environment.json](../evaluation/environment.json). Model: GGUF Q4_K_M;
25 steps, CFG 1, Euler/simple, denoise 1, aspect-preserving 1024 pixel budget.

| Measurement | Count | Minimum seconds | Median seconds | Maximum seconds |
|---|---|---|---|---|
| Completed outputs with timing | 40 | 178.056 | 197.5685 | 217.786 |
| Matched warm second seeds | 20 | 178.056 | 181.654 | 209.728 |

Sampled total-device peak VRAM: 7388 MiB.
Five-second sampling can miss short peaks and includes other desktop GPU usage.
Model-unloaded cold runs have warm operating-system file caches; they are not
machine cold boots. Exact cold-run records and delivered image dimensions are
in the [summary](../evaluation/summary_category_reference_v4.json). Restarted second seeds are
excluded from the matched warm set.
Some runs overlapped local CPU segmentation and container-build verification; these timings describe
the observed machine envelope, rather than an exclusive-machine speed comparison.

Recovered outputs with missing original history/timing/VRAM: 0.
Recovery verifies the PNG's embedded exact graph, source/uploaded bytes and output
hash; missing telemetry is never reconstructed and is excluded from metrics.

## Evidence and limits

- [Scores and per-output observations](../evaluation/SCORES_category_reference_v4.md).
- [Reviewed record manifest](../evaluation/reviewed_results_category_reference_v4.json).
- [Protocol and score anchors](../evaluation/PROTOCOL.md).
- [Inputs, rights and coverage](../evaluation/ASSETS.md).
- Local comparison gallery: `.local/evaluation_gallery_category_reference_v4.html`.

Only one AI reviewer compared source/reference/output images. This is an
engineering benchmark, not independent human approval, representative customer
accuracy, or physical sizing evidence. Five subjects and five reference garments
limit coverage; four subjects originate from upstream example imagery whose
synthetic status is unknown. Only visible garment details are graded.
Protected-region and multi-reference modes have no quality claim from this run.
The Qwen Image 2.1 model has separate research/evaluation terms; the application's
MIT license does not remove those restrictions.
