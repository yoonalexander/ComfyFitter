# Separate candidate protocol: reference_v2

Defined 2026-10-02 before execution. This is a new full candidate evaluation,
separate from the original `phase1_v1` and the accessory-only four-output ablation.
No selected seed or successful output replaces a failure in either benchmark.

Use all 20 original person/garment pairs and both original fixed seeds. The GGUF,
encoder, VAE, 25 steps, CFG 1, Euler/simple, denoise 1, 1024 pixel budget, batch 1
and Qwen cache settings remain unchanged. Category text remains the only dynamic
prompt field. Prompts explicitly preserve existing accessories/hair length and
match actual reference collar/closure details:

- `prompts/upper_body_reference_v2.txt`
- `prompts/outerwear_reference_v2.txt`

Because several wording changes are combined, this candidate does not establish
an independent causal effect of any one sentence. Report every outcome and use
the same five-dimensional scores, floors, 32/40 global gate and 8/10 category gate
as the original protocol. Apply no mask to these raw candidate outputs.

After reviewing raw outputs, a separate semantic-constraint study may transform
the complete matched set with the pinned CPU parser and the same fixed union,
growth, feather and protected-label rules. Retain both raw and constrained output
hashes and all failures. A four-image pilot is not sufficient to validate either
candidate or a production postprocessing default.

Run one inference batch at a time. Finish the original batch before requesting
model unloading or starting this candidate:

```powershell
& $evaluationPython evaluation\run_batch.py --experiment reference_v2 --cold-first --upper-body-prompt evaluation\prompts\upper_body_reference_v2.txt --outerwear-prompt evaluation\prompts\outerwear_reference_v2.txt
# After viewing/scoring every terminal output:
& $evaluationPython evaluation\publish_results.py --experiment reference_v2 --upper-body-prompt evaluation\prompts\upper_body_reference_v2.txt --outerwear-prompt evaluation\prompts\outerwear_reference_v2.txt
```

Retain the original scoring and any unsupported categories. No application or
hosted quality claim is implied before the relevant full gate passes.
