# Spatial-constraint investigation

2026-10-03. **The guarded CPU source-protection mode passed its full matched gate.**
This work addresses the preservation failures measured during Phase 1, as allowed
by the roadmap's dependency on measured failures. The original 40-output inference
benchmark remains unchanged.

The [guarded v5 report](SPATIAL_semantic_guarded_v5.md) compares all forty fresh
v4 outputs. Quality remains 36/40 (9/10 in every category), with no score
regression. Protection applies to nine outputs; thirty-one uncertain boundaries
fall back to the validated raw preview. Accepted protected-region changed pixels
decrease from 5,997,294 to zero. This measures exact pixel restoration, not a new
population accuracy estimate. The [unguarded v4](SPATIAL_semantic_conservative_v4.md)
was rejected, as were the earlier full studies.

All forty actual CPU-engine outputs and masks match the declared study, with
real CLI checks in each category. The asynchronous application adapter was also
exercised with its actual subprocess and normalizer, reproducing the study
pixels. Local admission checks report, implementation, runtime and model hashes.
The mode is optional, stays limited to one-reference jobs, and uses a 90-second
helper deadline with raw fallback. The hosted template leaves it disabled.

The investigation below records the earlier alternatives and their limitations.

## Selected direction and failed alternative

Explicitly marking broad garment polygons preserves source pixels outside the
edit area, but the first four-image pilot fails visual review. It restores the
source faces without glasses while leaving original green/brown collar and
shoulder patches. The resulting hybrid clothing and seams are unacceptable. All
four failures and their masks remain in `evaluation/benchmarks/spatial_pilot/`;
annotations are versioned under `evaluation/masks/`. Do not promote them.

The next candidate segments upper clothing in both the source and generated
image, uses their union to accommodate a new silhouette, feathers inward, and
subtracts protected source labels. Source face, hair, eyewear, hats, exposed
arms/hands and bags override the garment mask. Pixels outside the final editable
mask are copied from the source canvas and checked for exact equality.

This is an explicit constraint on the final returned image. It does not improve
the model's original generation or its reference fidelity. The constrained output
has separate hashes and a record linking to the retained original generation.
The original output remains available for comparison and fallback.

## Actual inference graph support

The pinned local ComfyUI exposes `LoadImageMask`, `VAEEncode`,
`SetLatentNoiseMask`, `ImageCompositeMasked` and image scaling nodes. Its
`TextEncodeQwenImage21` produces an **empty** sampling latent, rather than a
source-encoded latent. Simply attaching a noise mask to that empty latent would
not preserve the source outside it. Source-encoded masked sampling therefore
needs a changed graph and its own live evaluation. It is not claimed as tested.

The current candidate uses the existing generation graph followed by local
segmentation and compositing. This permits matched evaluation of exactly the
same source/reference/seed output without rerunning or changing inference.

## Preliminary matched observations

Single AI visual reviewer, the original two seeds for each pair:

| Pair | Original outputs passing | Coarse polygons passing | Semantic constraint passing |
|---|---|---|---|
| shirt_03 | 1/2 | 0/2 | 2/2 |
| hoodie_02 | 0/2 | 0/2 | 2/2 |

The semantic pilot restores eyewear-free faces while retaining the generated
shirt/hood designs. Fine hoodie lettering remains approximate and small edge or
wrist imperfections remain; artifact scores are 1. These four outcomes provide
no representative accuracy claim or approval of the other 36 outputs.

Two source/generated segmentations plus compositing took 6.00–6.43 seconds per
image on one CPU thread, excluding imports and model loading. This adds to the
original GPU generation time; it does not replace that time. The model file is
109,493,236 bytes, which is not a process-memory measurement. CPU peak memory was
not sampled for the first pilot. Subsequent runs record process peak working set,
including Python/Torch/library overhead, and model-residency RSS delta. No CUDA
allocation is requested by the constraint process. Concurrent CPU pilot work
occurred during portions of the original batch; its timings are a local runtime
envelope, not a controlled exclusive-machine speed comparison.

## Dependencies and terms

The locally downloaded parser is
[mattmdjaga/segformer_b2_clothes](https://huggingface.co/mattmdjaga/segformer_b2_clothes/tree/584abc1e1d260e23c0fc627c5217a09b2b461046),
revision `584abc1e1d260e23c0fc627c5217a09b2b461046`. Exact configuration/weight
hashes and runtime dependencies are in
[segmentation_environment.json](../evaluation/segmentation_environment.json).
Only safetensors and data/configuration files were downloaded; no remote model
code or pickle weights are executed. The runtime reads local files only and
never sends photos to a service. The model card points to NVIDIA's separate
research/evaluation license; see [third-party notices](../THIRD_PARTY_NOTICES.md).

## Retained limitations and checks

- Full matched review covers all twenty pairs and both seeds, including long
  hair, crossed hands, patterns and coat silhouettes. Coverage remains small.
- Verify that source and target segmentation errors do not clip new collars,
  retain old clothing, change unrelated garments, or produce boundary halos.
- Exposed-arm protection can prevent legitimate new sleeve coverage; provide
  reviewed mask refinement/fallback rather than claiming automatic correctness.
- CPU parser/compositing median is 6.33 seconds, excluding interpreter imports;
  observed process peak is 1,318.98 MiB. The actual adapter smoke took about
  15 seconds including its subprocess startup. Cached-mask compositing timings
  are reported separately and are not full application latency.
- Evaluate the revised inference prompt separately to resolve garment-detail
  failures such as substituted collars. Compositing cannot fix those failures.
- Require the complete quality gate before selecting a constrained workflow;
  keep the retained original output available as fallback.
