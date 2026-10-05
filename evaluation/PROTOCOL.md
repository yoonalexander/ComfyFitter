# Locked protocol: phase1_v1

Locked before the full run on 2026-09-30. No seed selection, prompt tuning, model substitution or exclusion of poor outputs is permitted within this benchmark. The initial two-image shirt pilot is retained with its original two seeds and settings; it is not cherry-picked.

## Dataset and inference

20 unique person/garment pairs, five in each of shirt, hoodie, jacket and coat. The [case manifest](cases/phase1.json) identifies inputs and visible garment features; the [asset manifest](assets_manifest.json) fixes bytes and attribution. Each pair runs once with each seed: `2026093001`, `2026093002`.

Use [qwen_tryon_upper_candidate_gguf.api.json](../workflows/qwen_tryon_upper_candidate_gguf.api.json), model `qwen_image_2.1_Q4_K_M.gguf`, encoder `qwen3vl_8b_w4a8.safetensors`, VAE `qwen_image_2.1_vae_bf16.safetensors`. Filenames alone do not identify binaries; checksums and source revisions are in [environment.json](environment.json).

`image_1` is the person, `image_2` is the garment. Shirts/hoodies use [upper_body.txt](prompts/upper_body.txt); jackets/coats use [outerwear.txt](prompts/outerwear.txt). Only the category placeholder changes. Steps 25, CFG 1, Euler, simple scheduler, denoise 1, aspect-preserving resolution budget 1024, batch 1, Qwen cache enabled. No segmentation, masking, prompt enhancer, or extra references.

## Score anchors

| Dimension | 0: unacceptable | 1: noticeable defect | 2: intended preview quality |
|---|---|---|---|
| Identity | Different or severely altered person | Recognizable person with changed face, hair, or added/removed personal accessories | Recognizable facial features, hair and accessories preserved |
| Body/pose | Major reshaping, wrong pose or missing limbs | Noticeable proportion, arm, hand or stance drift | Original body proportions and pose retained, allowing the new garment's natural silhouette/occlusion |
| Garment transfer | Recolor only, wrong garment or absent transfer | Correct general garment with materially wrong visible collar, closure, pockets, pattern, print or silhouette | Visible reference design features transferred with plausible drape; legitimately hidden details are not graded |
| Background/lighting | Replaced scene or incoherent illumination | Noticeable background or lighting drift, still usable | Scene, camera viewpoint and illumination remain consistent |
| Artifacts | Severe anatomy, edge or texture defects | Minor visible imperfections | No obvious distracting defects at delivered size |

A changed wearing state such as an open shirt can be acceptable when the design and garment identity remain intact. A longer coat covering a skirt is legitimate occlusion; changing the skirt where it remains visible is unintended editing. Do not reward synthetic realism at the expense of identity, pose or reference fidelity. Do not infer exact sizing or fit.

Pass: identity/body-pose/garment-transfer each equal 2, background/lighting and artifacts each at least 1. Global gate: at least 32/40 pass **and** every supported category at least 8/10. A failed execution remains in its denominator. Missing or duplicate evidence cannot pass. Complete evaluation and a passed quality gate are distinct outcomes.

One Codex visual reviewer compares all three images, recording an explanation for every output. This is preliminary engineering review, not human approval, blinded review, a population accuracy estimate or customer acceptance.

After completing this fixed run, a separate accessory-wording ablation may compare `shirt_03` and `hoodie_02` using the same two seeds, models, inputs and sampler settings. Its alternate prompt removes the unconditional `glasses` list entry and explicitly preserves the source's existing accessories. These four outputs remain under `benchmarks/`, do not replace failed baseline outputs, and cannot validate a changed workflow without a fresh full gate.

## Performance

Record ComfyUI's execution-start/success timestamps and separately the runner's wall time, including polling delay. Before the first new batch case, request model unloading on an idle dedicated server; retain that first seed as model-residency cold and its second as the matched warm run. Operating-system file caches remain warm; this is not cold-boot measurement. Other first seeds include changed inputs and re-encoding; second seeds reuse graph intermediates.

Sample `nvidia-smi` every five seconds during each run. Report the maximum total device memory observed, with the caveat that desktop use is included and brief peaks may be missed. Retain failures, graph snapshots, input/output hashes, prompt IDs and histories in ignored result directories. Publish scores and metrics only after the local evidence validator succeeds.
