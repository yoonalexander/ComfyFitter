# Phase 1 evaluation

These scripts evaluate the inference workflow and its optional reference and protection modes. Application admission uses the published reports and exact graph/prompt hashes.

The protocol uses 20 pairs and seeds `2026093001` / `2026093002`: 40 outputs, including failed executions. Five scores range from 0 (unacceptable), through 1 (noticeable defects), to 2 (intended preview quality). Identity, body/pose and garment transfer must each score 2; background/lighting and artifacts must each score at least 1. Added/removed accessories count against preservation; a recolor or substantially different reference detail counts against transfer. Judge only visible reference features; features hidden by the legitimate pose cannot be assessed. Do not infer physical fit.

The locked gate requires 32 passing outputs overall and 8 per category. Scores and explicit evidence notes come from Codex visual comparison of each source, reference and output. This is one AI reviewer, not independent human or blind validation. Unit-test fixtures are not evaluation evidence.

See [SETUP](../docs/SETUP.md) for the measured runtime and the isolated local server. Use its ComfyUI virtual-environment Python, or a separate Python environment with `Pillow==12.3.0` for these scripts. Example commands from the repository root, with `$evaluationPython` pointing to that executable:

```powershell
& $evaluationPython evaluation\fetch_assets.py
& $evaluationPython evaluation\phase1.py preflight
& $evaluationPython evaluation\run_case.py --case shirt_01
# Reconcile an interrupted existing run; never generate duplicate seeds blindly.
& $evaluationPython evaluation\run_case.py --case jacket_01 --resume
# Alternative: sequential whole dataset, reusing reconciled terminal runs.
# --cold-first unloads models on an idle dedicated server before the first new case.
& $evaluationPython evaluation\run_batch.py --cold-first
& $evaluationPython -m unittest discover -s evaluation -p 'test_*.py'
# After viewing and scoring every terminal result:
& $evaluationPython evaluation\publish_results.py
& $evaluationPython evaluation\phase1.py summarize --records evaluation\reviewed_results.json
```

`run_case.py` sends images only to loopback. It retains the exact graph, input hashes, prompt ID, history, output hash, execution time and five-second device VRAM samples. Images and run directories remain ignored. Fill in `scores`, `reviewer`, and `notes` only after viewing the output. No automatic quality score or retry substitutes for review. Interrupted/uncertain submissions require history/queue reconciliation before rerunning. The batch runner stops on unresolved cases and does not discard failed generations.

All Phase 1 category results use the GGUF workflow. The optional `--model int8` switch is for separate experiments; do not mix those results into the locked GGUF gate. Model unloading measures model-residency cold latency with a warm operating-system disk cache, not a machine cold boot. The model's own `QwenImage21Cache` node remains enabled. Sampled VRAM is total device usage, including desktop applications; it can miss brief peaks.

The optional accessory ablation uses a separate prompt and output directory:

```powershell
& $evaluationPython evaluation\run_case.py --case shirt_03 --experiment accessory_wording --prompt-template evaluation\prompts\upper_body_accessory_ablation.txt
& $evaluationPython evaluation\run_case.py --case hoodie_02 --experiment accessory_wording --prompt-template evaluation\prompts\upper_body_accessory_ablation.txt
```

Run these after the locked batch is finished so they do not interfere with matched warm timings. They compare four matched outputs and are excluded from the 40-output gate. A revised prompt still needs the full gate before it becomes a validated workflow.

Keep licensed benchmark assets and execution outputs for regression checks. This is evaluation retention, not the future application's 24-hour upload policy. Attribution is in [ASSETS.md](ASSETS.md).

After a server restart, its in-memory history may be lost even when a saved PNG
survives. `--resume` can recover exactly one local output whose embedded graph
matches the saved job graph. It retains missing original timing/VRAM as unavailable
and never synthesizes history. The publisher validates the embedded graph and
output hash, lists recovered outputs, and excludes missing telemetry from timing
statistics. A live queued job or an uncertain job without unique verifiable output
requires reconciliation before any resubmission.

A revised prompt can receive a fresh, separate 40-output evaluation after the
small ablation. This never substitutes results into the original locked batch:

```powershell
& $evaluationPython evaluation\run_batch.py --experiment accessory_v2 --cold-first --upper-body-prompt evaluation\prompts\upper_body_accessory_ablation.txt --outerwear-prompt evaluation\prompts\outerwear_accessory_ablation.txt
# After visually reviewing and scoring all 40 experiment outputs:
& $evaluationPython evaluation\publish_results.py --experiment accessory_v2 --upper-body-prompt evaluation\prompts\upper_body_accessory_ablation.txt --outerwear-prompt evaluation\prompts\outerwear_accessory_ablation.txt
```

The experiment receives distinct score, summary, reviewed-record, and gallery
artifacts. Both protocols require the same complete dataset, seeds, score floors
and 32/40 overall plus 8/10 per-category thresholds. Restarted second seeds are
excluded from matched warm measurements.

The [reference_v2 protocol](REFERENCE_V2_PROTOCOL.md) defines the next full
candidate after observing both accessory changes and substituted jacket collars.
It combines preservation and reference-detail wording changes without changing
the dataset, seed pair or acceptance thresholds.

The [spatial investigation](../docs/SPATIAL_CONSTRAINTS.md) keeps postprocessing
evidence separate. `protected_regions.py` evaluates explicit polygons;
`semantic_constraints.py` evaluates the pinned, locally supplied CPU parser.
Neither uploads photos or assigns visual scores. Their derived PNGs are not
original ComfyUI outputs and must not be inserted into the original gate.

## Category-specific candidate and feature studies

`category_reference_v4_protocol.json` declares a fresh full 40-output candidate:
upper-body reference_v2, jacket reference_v2, and coat reference_v3 prompts.
It preserves the original pairs, seeds and thresholds. Generate and publish it
with the same explicit prompt paths:

```powershell
& $evaluationPython evaluation\run_batch.py --experiment category_reference_v4 --cold-first --upper-body-prompt evaluation\prompts\upper_body_reference_v2.txt --outerwear-prompt evaluation\prompts\outerwear_reference_v3.txt --jacket-prompt evaluation\prompts\outerwear_reference_v2.txt
& $evaluationPython evaluation\publish_results.py --experiment category_reference_v4 --upper-body-prompt evaluation\prompts\upper_body_reference_v2.txt --outerwear-prompt evaluation\prompts\outerwear_reference_v3.txt --jacket-prompt evaluation\prompts\outerwear_reference_v2.txt
```

Previous reviews may be carried over only when decoded RGB pixels, dimensions,
source/reference bytes and prompts match exactly. Record that proof in each
review note. PNG metadata differences alone do not establish visual differences.
New pixels always require visual review; generation never assigns scores.

The declared multiple-reference study retains eight matched quality outputs and
two separate five-input capacity outputs. Its genuine jacket back photo and
licensed detail crops are recorded in `reference_assets.json`. The capacity
sample explicitly repeats the front image in the side slot; it tests execution
capacity and does not establish side-view fidelity. The two-garment study retains
sixteen outputs with independent inner, outer and occlusion scores.

```powershell
& $evaluationPython evaluation\run_reference_study.py --protocol evaluation\multiple_reference_v1_protocol.json --wait-for-baseline
& $evaluationPython evaluation\reference_sheet.py --experiment multiple_reference_v1
& $evaluationPython evaluation\run_reference_study.py --protocol evaluation\two_garment_v1_protocol.json --wait-for-baseline
& $evaluationPython evaluation\reference_sheet.py --experiment two_garment_v1
# After reviewing every feature output and its matched raw output:
& $evaluationPython evaluation\publish_references.py
```

Reference studies retain submission intent before POST. An existing nonterminal
record requires reconciliation rather than automatic resubmission. Do not alter
their pinned implementation, graph, inputs or protocols while a study is running.

The v1 jacket back/detail study showed an unrelated-clothing preservation
regression. The predeclared `multiple_reference_v2_protocol.json` therefore
tests eight fresh hoodie-detail outputs across four subjects, with the same
seeds, prompts and scoring rules. Its five-input capacity evidence is separately
linked to the original protocol checksum and fully revalidated; earlier quality
outputs never replace fresh v2 outputs. Neither jacket views nor a duplicate
front in the side slot establishes a qualified view for users.

```powershell
& $evaluationPython evaluation\run_reference_study.py --protocol evaluation\multiple_reference_v2_protocol.json --wait-for-baseline
& $evaluationPython evaluation\reference_sheet.py --experiment multiple_reference_v2
# After all original, fresh and outfit outputs have independent reviews:
& $evaluationPython evaluation\publish_references.py --reference-experiment multiple_reference_v2
```

Publication retains every original rejection alongside the selected study and
keeps capacity measurements separate from matched quality measurements.

The original full outfit matrix failed: shirt+jacket 2/8, shirt+coat 6/8.
`two_garment_v2_protocol.json` declares a fresh full sixteen-output refinement
using the same pairs, seeds, graph and scoring floors. The separately pinned
`backend/app/outfits.py` adds collar architecture, wrist/object contact and visible
lower-clothing constraints. Original reference logic remains unchanged; outfit
admission additionally checks this module's hash. Retain all sixteen new outputs,
including failures, rather than replacing only failed original cases.

That complete refinement finished at 5/8 for both pairs and remains rejected.
`two_garment_v3_protocol.json` narrows the next launch experiment to shirt+coat,
retaining all four ORIGINAL coat subjects and both fixed seeds, with eight FRESH
outputs and the unchanged 7/8 floor. No earlier good quality row is reused.
`backend/app/coat_outfits.py` independently binds the tucked-shirt/original-lower-
clothing and reference-collar refinement, preserving both earlier modules.
Only this exact coat pair can qualify the eight-output study; jackets remain
excluded. Its module, complete count and original threshold are checked by the app.

The completed v3 study also rejected at 5/8. Its final native result exceeded the
900-second evaluator wait and was recovered from the exact owned successful
history/graph/PNG without another submission. Native time is known; wall time and
complete VRAM sampling are explicitly unavailable for that one result.
`two_garment_v4_protocol.json` declares eight more fresh outputs on all original
coat subjects/seeds with the unchanged 7/8 floor. The independently pinned
`backend/app/bag_coat_outfits.py` adds existing bag/strap preservation and explicit
inner-shirt closure copying to the unchanged v3 prompt. Its predeclared evaluator
wait is 1800 seconds to accommodate observed long native runs; this changes no
inference setting, score or denominator.

```powershell
& $evaluationPython evaluation\run_reference_study.py --protocol evaluation\two_garment_v4_protocol.json --wait-for-baseline
& $evaluationPython evaluation\reference_sheet.py --experiment two_garment_v4
& $evaluationPython evaluation\publish_references.py --reference-experiment multiple_reference_v2 --outfit-experiment two_garment_v4
```

```powershell
& $evaluationPython evaluation\run_reference_study.py --protocol evaluation\two_garment_v3_protocol.json --wait-for-baseline
& $evaluationPython evaluation\reference_sheet.py --experiment two_garment_v3
& $evaluationPython evaluation\publish_references.py --reference-experiment multiple_reference_v2 --outfit-experiment two_garment_v3
```

```powershell
& $evaluationPython evaluation\run_reference_study.py --protocol evaluation\two_garment_v2_protocol.json --wait-for-baseline
& $evaluationPython evaluation\reference_sheet.py --experiment two_garment_v2
& $evaluationPython evaluation\publish_references.py --reference-experiment multiple_reference_v2 --outfit-experiment two_garment_v2
```

`two_garment_v5_protocol.json` declares another complete fresh eight-output coat
matrix with the same images, seeds and 7/8 floor. The application and study both
use the explicit `source_has_bag` boolean: true only for the studio source which
already has a backpack, false for the other three original subjects. The bag
preservation sentence is omitted for bag-free photos; the shirt-closure sentence
remains in both branches. `backend/app/conditional_coat_outfits.py` is separately
hash-bound, and admission additionally requires both declared bag choices. None
of the earlier successful quality outputs substitute for fresh V5 outputs.

A stalled V4 native text-encoder execution remained active for over eight hours.
Its evaluator had exited, and a verified sole-owned interrupt did not release it.
The dedicated worker was restarted after retaining the exact queue/client/graph
ownership evidence. That original submission remains a failure in the fixed
matrix, with a hash-bound interruption/exit audit and no invented output, native
success history, execution time, wall time or complete VRAM sample. Publication
checks this distinct failure evidence; it cannot qualify as a visual pass.

```powershell
& $evaluationPython evaluation\run_reference_study.py --protocol evaluation\two_garment_v5_protocol.json --wait-for-baseline
& $evaluationPython evaluation\reference_sheet.py --experiment two_garment_v5
& $evaluationPython evaluation\publish_references.py --reference-experiment multiple_reference_v2 --outfit-experiment two_garment_v5
```

`semantic_conservative_v4` and `semantic_guarded_v5` compare CPU source restoration
with the same fresh raw outputs. The guard falls back to raw when a protected
boundary would be discontinuous. Their reports reconstruct every mask, pixel
output and metric from pinned source/parser evidence. The application also
requires all forty actual CPU-engine outputs and masks to match the study, with
real helper-process checks in all four categories, before protection admission.

```powershell
& $evaluationPython evaluation\matched_sheet.py --experiment semantic_guarded_v5
& $evaluationPython evaluation\publish_spatial.py --experiment semantic_conservative_v4 --source-experiment category_reference_v4
& $evaluationPython evaluation\publish_spatial.py --experiment semantic_guarded_v5 --source-experiment category_reference_v4
```

The application modes have separate gates: a passing single-garment report cannot
enable multiple views, layered garments or protection by itself.


Evidence admission binds exact file bytes. `.gitattributes` disables line-ending
conversion for backend, evaluation and workflow files while retaining ordinary
text diffs. Preserve that file when cloning or preparing images; changing a
pinned module, graph, prompt, protocol or report requires fresh matching evidence.


The complete V5 conditional-bag matrix passed 7/8. All eight fresh outputs have
independent visual scores and source/upload/native-history/graph/embedded-PNG
validation. The final field seed still fails inner-shirt neckline/closure fidelity;
that failure remains visible. Local median 282.1455 seconds, sampled device peak
7,680 MiB. Only shirt+coat is offered, with both declared source-bag choices.
Original and V2-V4 rejected studies are retained in the same published report.
