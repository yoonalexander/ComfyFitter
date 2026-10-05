# Matched spatial study: semantic_occlusion_v2

Decision: **rejected**. Reviewed all 40 fixed outputs, including 2 raw fallbacks. Passing previews: 28/40 versus raw 31/40. Category counts: {'shirt': 8, 'hoodie': 8, 'jacket': 10, 'coat': 2}.

Every source, raw output, mask and constrained output hash was checked. Masks and final pixels were reconstructed from retained parser labels; exact source pixels outside the editable mask were verified. This pixel guarantee does not establish garment fidelity or good boundaries.

Matched score changes: `{"identity": {"improved": 2, "unchanged": 38, "regressed": 0, "total": 2}, "body_pose": {"improved": 1, "unchanged": 39, "regressed": 0, "total": 1}, "garment_transfer": {"improved": 0, "unchanged": 34, "regressed": 6, "total": -6}, "background_lighting": {"improved": 0, "unchanged": 40, "regressed": 0, "total": 0}, "artifacts": {"improved": 3, "unchanged": 31, "regressed": 6, "total": -3}}`. The visible original blouse remains incorrectly restored in several outputs. No spatial mode is enabled by this study.

CPU parser plus original compositing: `{'count': 40, 'minimum': 5.485461, 'median': 5.993148, 'maximum': 8.483856}` seconds. Revised cached compositing: `{'count': 40, 'minimum': 0.248113, 'median': 0.452681, 'maximum': 0.523127}` seconds, where present. Cold model loading: `{'count': 20, 'minimum': 0.16673, 'median': 0.1740255, 'maximum': 0.19495}` seconds, measured separately. CPU process peak: 1316.145 MiB. Revised runs reuse parser labels; their compositing timing is not a new full parser measurement. Python import startup is excluded. Original GPU generation telemetry remains in the raw reference_v2 report; no GPU work was resubmitted.

Single AI visual reviewer; see ASSETS.md for source rights. Scores: identity / body-pose / garment / background / artifacts.

| Case | Seed | Scores | Mode | Observation |
|---|---|---|---|
| shirt_01 | 2026093001 | 2 / 2 / 2 / 2 / 2 | Applied | Matched source/reference/raw/constrained comparison: visible garment structure, face, pose and surrounding scene retained. |
| shirt_01 | 2026093002 | 2 / 2 / 2 / 2 / 2 | Applied | Matched source/reference/raw/constrained comparison: visible garment structure, face, pose and surrounding scene retained. |
| shirt_02 | 2026093001 | 2 / 2 / 2 / 2 / 1 | Applied | Matched source/reference/raw/constrained comparison: visible garment structure, face, pose and surrounding scene retained. Thin neck boundary or approximate fine printed lettering remains visible. |
| shirt_02 | 2026093002 | 2 / 2 / 2 / 2 / 1 | Applied | Matched source/reference/raw/constrained comparison: visible garment structure, face, pose and surrounding scene retained. Thin neck boundary or approximate fine printed lettering remains visible. |
| shirt_03 | 2026093001 | 2 / 2 / 2 / 2 / 2 | Applied | Matched source/reference/raw/constrained comparison: visible garment structure, face, pose and surrounding scene retained. |
| shirt_03 | 2026093002 | 2 / 2 / 2 / 2 / 2 | Applied | Matched source/reference/raw/constrained comparison: visible garment structure, face, pose and surrounding scene retained. |
| shirt_04 | 2026093001 | 2 / 2 / 2 / 2 / 2 | Applied | Matched source/reference/raw/constrained comparison: visible garment structure, face, pose and surrounding scene retained. |
| shirt_04 | 2026093002 | 2 / 2 / 2 / 2 / 2 | Applied | Matched source/reference/raw/constrained comparison: visible garment structure, face, pose and surrounding scene retained. |
| shirt_05 | 2026093001 | 2 / 2 / 1 / 2 / 2 | Applied | Rejected: protected source hair/clothing segmentation pastes a large pink blouse patch over the replacement garment, despite preserving source hair and face. |
| shirt_05 | 2026093002 | 2 / 2 / 1 / 2 / 2 | Applied | Rejected: protected source hair/clothing segmentation pastes a large pink blouse patch over the replacement garment, despite preserving source hair and face. |
| hoodie_01 | 2026093001 | 2 / 2 / 2 / 2 / 1 | Applied | Matched source/reference/raw/constrained comparison: visible garment structure, face, pose and surrounding scene retained. Thin neck boundary or approximate fine printed lettering remains visible. |
| hoodie_01 | 2026093002 | 2 / 2 / 2 / 2 / 1 | Applied | Matched source/reference/raw/constrained comparison: visible garment structure, face, pose and surrounding scene retained. Thin neck boundary or approximate fine printed lettering remains visible. |
| hoodie_02 | 2026093001 | 2 / 2 / 2 / 2 / 1 | Applied | Matched source/reference/raw/constrained comparison: visible garment structure, face, pose and surrounding scene retained. Thin neck boundary or approximate fine printed lettering remains visible. |
| hoodie_02 | 2026093002 | 2 / 2 / 2 / 2 / 1 | Applied | Matched source/reference/raw/constrained comparison: visible garment structure, face, pose and surrounding scene retained. Thin neck boundary or approximate fine printed lettering remains visible. |
| hoodie_03 | 2026093001 | 2 / 2 / 2 / 2 / 1 | Applied | Matched source/reference/raw/constrained comparison: visible garment structure, face, pose and surrounding scene retained. Thin neck boundary or approximate fine printed lettering remains visible. |
| hoodie_03 | 2026093002 | 2 / 2 / 2 / 2 / 1 | Applied | Matched source/reference/raw/constrained comparison: visible garment structure, face, pose and surrounding scene retained. Thin neck boundary or approximate fine printed lettering remains visible. |
| hoodie_04 | 2026093001 | 2 / 2 / 2 / 2 / 1 | Applied | Matched source/reference/raw/constrained comparison: visible garment structure, face, pose and surrounding scene retained. Thin neck boundary or approximate fine printed lettering remains visible. |
| hoodie_04 | 2026093002 | 2 / 2 / 2 / 2 / 1 | Applied | Matched source/reference/raw/constrained comparison: visible garment structure, face, pose and surrounding scene retained. Thin neck boundary or approximate fine printed lettering remains visible. |
| hoodie_05 | 2026093001 | 2 / 2 / 1 / 2 / 2 | Applied | Rejected: protected source hair/clothing segmentation pastes a large pink blouse patch over the replacement garment, despite preserving source hair and face. |
| hoodie_05 | 2026093002 | 2 / 2 / 1 / 2 / 2 | Applied | Rejected: protected source hair/clothing segmentation pastes a large pink blouse patch over the replacement garment, despite preserving source hair and face. |
| jacket_01 | 2026093001 | 2 / 2 / 2 / 2 / 2 | Applied | Matched source/reference/raw/constrained comparison: visible garment structure, face, pose and surrounding scene retained. |
| jacket_01 | 2026093002 | 2 / 2 / 2 / 2 / 2 | Applied | Matched source/reference/raw/constrained comparison: visible garment structure, face, pose and surrounding scene retained. |
| jacket_02 | 2026093001 | 2 / 2 / 2 / 2 / 1 | Applied | Matched source/reference/raw/constrained comparison: visible garment structure, face, pose and surrounding scene retained. Thin neck boundary or approximate fine printed lettering remains visible. |
| jacket_02 | 2026093002 | 2 / 2 / 2 / 2 / 1 | Applied | Matched source/reference/raw/constrained comparison: visible garment structure, face, pose and surrounding scene retained. Thin neck boundary or approximate fine printed lettering remains visible. |
| jacket_03 | 2026093001 | 2 / 2 / 2 / 2 / 1 | Applied | Matched source/reference/raw/constrained comparison: visible garment structure, face, pose and surrounding scene retained. Thin neck boundary or approximate fine printed lettering remains visible. |
| jacket_03 | 2026093002 | 2 / 2 / 2 / 2 / 1 | Applied | Matched source/reference/raw/constrained comparison: visible garment structure, face, pose and surrounding scene retained. Thin neck boundary or approximate fine printed lettering remains visible. |
| jacket_04 | 2026093001 | 2 / 2 / 2 / 2 / 2 | Applied | Refinement restores the visible pale source skirt in seed one while keeping the red fringed jacket, face and side pose; seed two also retains the skirt. |
| jacket_04 | 2026093002 | 2 / 2 / 2 / 2 / 2 | Applied | Refinement restores the visible pale source skirt in seed one while keeping the red fringed jacket, face and side pose; seed two also retains the skirt. |
| jacket_05 | 2026093001 | 2 / 2 / 2 / 2 / 2 | Raw fallback | Raw-image fallback reviewed: Matched source/reference/raw/constrained comparison: visible garment structure, face, pose and surrounding scene retained. |
| jacket_05 | 2026093002 | 2 / 2 / 2 / 2 / 2 | Raw fallback | Raw-image fallback reviewed: Matched source/reference/raw/constrained comparison: visible garment structure, face, pose and surrounding scene retained. |
| coat_01 | 2026093001 | 2 / 2 / 2 / 2 / 2 | Applied | Matched source/reference/raw/constrained comparison: visible garment structure, face, pose and surrounding scene retained. |
| coat_01 | 2026093002 | 2 / 2 / 2 / 2 / 2 | Applied | Matched source/reference/raw/constrained comparison: visible garment structure, face, pose and surrounding scene retained. |
| coat_02 | 2026093001 | 2 / 2 / 1 / 2 / 1 | Applied | Rejected: wrong standing collar and/or short visible jacket hem instead of the reference pointed collar and long coat. Mask does not correct these errors. |
| coat_02 | 2026093002 | 2 / 2 / 1 / 2 / 1 | Applied | Rejected: wrong standing collar and/or short visible jacket hem instead of the reference pointed collar and long coat. Mask does not correct these errors. |
| coat_03 | 2026093001 | 2 / 2 / 1 / 2 / 2 | Applied | Rejected: wrong standing collar and/or short visible jacket hem instead of the reference pointed collar and long coat. Mask does not correct these errors. |
| coat_03 | 2026093002 | 2 / 2 / 1 / 2 / 2 | Applied | Rejected: wrong standing collar and/or short visible jacket hem instead of the reference pointed collar and long coat. Mask does not correct these errors. |
| coat_04 | 2026093001 | 2 / 2 / 1 / 2 / 2 | Applied | Rejected: wrong standing collar and/or short visible jacket hem instead of the reference pointed collar and long coat. Mask does not correct these errors. |
| coat_04 | 2026093002 | 2 / 2 / 1 / 2 / 2 | Applied | Rejected: wrong standing collar and/or short visible jacket hem instead of the reference pointed collar and long coat. Mask does not correct these errors. |
| coat_05 | 2026093001 | 2 / 2 / 1 / 2 / 2 | Applied | Rejected: protected source hair/clothing segmentation pastes a large pink blouse patch over the replacement garment, despite preserving source hair and face. |
| coat_05 | 2026093002 | 2 / 2 / 1 / 2 / 2 | Applied | Rejected: protected source hair/clothing segmentation pastes a large pink blouse patch over the replacement garment, despite preserving source hair and face. |
