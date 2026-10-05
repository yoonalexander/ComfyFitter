# Matched spatial study: semantic_full_v3

Decision: **rejected**. Reviewed all 40 fixed outputs, including 8 raw fallbacks. Passing previews: 23/40 versus raw 31/40. Category counts: {'shirt': 8, 'hoodie': 8, 'jacket': 7, 'coat': 0}.

Every source, raw output, mask and constrained output hash was checked. Masks and final pixels were reconstructed from retained parser labels; exact source pixels outside the editable mask were verified. This pixel guarantee does not establish garment fidelity or good boundaries.

Matched score changes: `{"identity": {"improved": 2, "unchanged": 38, "regressed": 0, "total": 2}, "body_pose": {"improved": 0, "unchanged": 40, "regressed": 0, "total": 0}, "garment_transfer": {"improved": 0, "unchanged": 30, "regressed": 10, "total": -10}, "background_lighting": {"improved": 0, "unchanged": 40, "regressed": 0, "total": 0}, "artifacts": {"improved": 0, "unchanged": 24, "regressed": 16, "total": -16}}`. The visible original blouse remains incorrectly restored in several outputs. No spatial mode is enabled by this study.

CPU parser plus original compositing: `{'count': 40, 'minimum': 5.485461, 'median': 5.993148, 'maximum': 8.483856}` seconds. Revised cached compositing: `{'count': 0, 'minimum': None, 'median': None, 'maximum': None}` seconds, where present. Cold model loading: `{'count': 20, 'minimum': 0.16673, 'median': 0.1740255, 'maximum': 0.19495}` seconds, measured separately. CPU process peak: 1316.145 MiB. Revised runs reuse parser labels; their compositing timing is not a new full parser measurement. Python import startup is excluded. Original GPU generation telemetry remains in the raw reference_v2 report; no GPU work was resubmitted.

Single AI visual reviewer; see ASSETS.md for source rights. Scores: identity / body-pose / garment / background / artifacts.

| Case | Seed | Scores | Mode | Observation |
|---|---|---|---|
| shirt_01 | 2026093001 | 2 / 2 / 2 / 2 / 2 | Applied | Compared raw/source/reference and constrained output: identity, pose and visible design retained. |
| shirt_01 | 2026093002 | 2 / 2 / 2 / 2 / 2 | Applied | Compared raw/source/reference and constrained output: identity, pose and visible design retained. |
| shirt_02 | 2026093001 | 2 / 2 / 2 / 2 / 1 | Applied | Face/hair/pose and visible reference design retained; a thin dark source neck boundary is visible after compositing. |
| shirt_02 | 2026093002 | 2 / 2 / 2 / 2 / 1 | Applied | Face/hair/pose and visible reference design retained; a thin dark source neck boundary is visible after compositing. |
| shirt_03 | 2026093001 | 2 / 2 / 2 / 2 / 2 | Applied | Compared raw/source/reference and constrained output: identity, pose and visible design retained. |
| shirt_03 | 2026093002 | 2 / 2 / 2 / 2 / 2 | Applied | Compared raw/source/reference and constrained output: identity, pose and visible design retained. |
| shirt_04 | 2026093001 | 2 / 2 / 2 / 2 / 2 | Raw fallback | Parser fallback retains the raw preview: Curly hair/face/smile, turned pose/arm position and coastal light/background retained. Light-blue denim upper shirt replaces the white ruffled top, with pointed collar, pale buttons and long cuffed sleeves. Side view hides much of the chest pocket/front; white lower skirt remains. |
| shirt_04 | 2026093002 | 2 / 2 / 2 / 2 / 2 | Raw fallback | Parser fallback retains the raw preview: Face/smile, curls, turned pose and coastal scene retained. Denim blue shirt transfers the pointed collar, visible pale placket buttons and cuffed sleeves; chest pocket is partly hidden by the side angle. Lower skirt/waist sash remain visible where the new shirt permits. |
| shirt_05 | 2026093001 | 2 / 2 / 1 / 2 / 1 | Applied | Original hair and exposed arms return, but large old pink clothing patches remain in the new garment chest and sleeve regions. Garment construction is broken; mask policy rejected. |
| shirt_05 | 2026093002 | 2 / 2 / 1 / 2 / 1 | Applied | Original hair and exposed arms return, but large old pink clothing patches remain in the new garment chest and sleeve regions. Garment construction is broken; mask policy rejected. |
| hoodie_01 | 2026093001 | 2 / 2 / 2 / 2 / 1 | Applied | Face/hair/pose and visible reference design retained. Fine garment text or minor lower texture remains approximate. |
| hoodie_01 | 2026093002 | 2 / 2 / 2 / 2 / 1 | Applied | Face/hair/pose and visible reference design retained. Fine garment text or minor lower texture remains approximate. |
| hoodie_02 | 2026093001 | 2 / 2 / 2 / 2 / 1 | Applied | Face/hair/pose and visible reference design retained; a thin dark source neck boundary is visible after compositing. |
| hoodie_02 | 2026093002 | 2 / 2 / 2 / 2 / 1 | Applied | Face/hair/pose and visible reference design retained; a thin dark source neck boundary is visible after compositing. |
| hoodie_03 | 2026093001 | 2 / 2 / 2 / 2 / 1 | Applied | Face/hair/pose and visible reference design retained. Fine garment text or minor lower texture remains approximate. |
| hoodie_03 | 2026093002 | 2 / 2 / 2 / 2 / 1 | Applied | Face/hair/pose and visible reference design retained. Fine garment text or minor lower texture remains approximate. |
| hoodie_04 | 2026093001 | 2 / 2 / 2 / 2 / 1 | Raw fallback | Parser fallback retains the raw preview: Visible hood, chest flames/outlined print, sleeve stars and lettering transfer; face, short curls, pose and coastal scene retained. Fine lettering is approximate. |
| hoodie_04 | 2026093002 | 2 / 2 / 2 / 2 / 1 | Raw fallback | Parser fallback retains the raw preview: Visible hood, chest flames/outlined print, sleeve stars and lettering transfer; face, short curls, pose and coastal scene retained. Fine lettering is approximate. |
| hoodie_05 | 2026093001 | 2 / 2 / 1 / 2 / 1 | Applied | Original hair and exposed arms return, but large old pink clothing patches remain in the new garment chest and sleeve regions. Garment construction is broken; mask policy rejected. |
| hoodie_05 | 2026093002 | 2 / 2 / 1 / 2 / 1 | Applied | Original hair and exposed arms return, but large old pink clothing patches remain in the new garment chest and sleeve regions. Garment construction is broken; mask policy rejected. |
| jacket_01 | 2026093001 | 2 / 2 / 2 / 2 / 2 | Applied | Compared raw/source/reference and constrained output: identity, pose and visible design retained. |
| jacket_01 | 2026093002 | 2 / 2 / 2 / 2 / 2 | Applied | Compared raw/source/reference and constrained output: identity, pose and visible design retained. |
| jacket_02 | 2026093001 | 2 / 2 / 2 / 2 / 1 | Applied | Face/hair/pose and visible reference design retained; a thin dark source neck boundary is visible after compositing. |
| jacket_02 | 2026093002 | 2 / 2 / 2 / 2 / 1 | Applied | Face/hair/pose and visible reference design retained; a thin dark source neck boundary is visible after compositing. |
| jacket_03 | 2026093001 | 2 / 2 / 2 / 2 / 1 | Applied | Face/hair/pose and visible reference design retained. Fine garment text or minor lower texture remains approximate. |
| jacket_03 | 2026093002 | 2 / 2 / 2 / 2 / 1 | Applied | Face/hair/pose and visible reference design retained. Fine garment text or minor lower texture remains approximate. |
| jacket_04 | 2026093001 | 2 / 1 / 2 / 2 / 1 | Raw fallback | Parser fallback retains the raw preview: Burgundy velvet, embroidered broad collar and fringe transfer, but the visible original pale skirt is replaced with dark fabric below the cropped hem. Unrelated lower clothing is not preserved. |
| jacket_04 | 2026093002 | 2 / 2 / 2 / 2 / 2 | Raw fallback | Parser fallback retains the raw preview: Burgundy velvet, broad embroidered collar, fringed cuffs and cropped hem transfer. Face, curls, side pose, pale skirt and coastal background retained. |
| jacket_05 | 2026093001 | 2 / 2 / 1 / 2 / 1 | Applied | Original hair and exposed arms return, but large old pink clothing patches remain in the new garment chest and sleeve regions. Garment construction is broken; mask policy rejected. |
| jacket_05 | 2026093002 | 2 / 2 / 1 / 2 / 1 | Applied | Original hair and exposed arms return, but large old pink clothing patches remain in the new garment chest and sleeve regions. Garment construction is broken; mask policy rejected. |
| coat_01 | 2026093001 | 2 / 2 / 1 / 2 / 1 | Applied | Mask restores original pants across the new long coat, cutting its lower silhouette at the hips. Source identity is protected but coat transfer is degraded. |
| coat_01 | 2026093002 | 2 / 2 / 1 / 2 / 1 | Applied | Mask restores original pants across the new long coat, cutting its lower silhouette at the hips. Source identity is protected but coat transfer is degraded. |
| coat_02 | 2026093001 | 2 / 2 / 1 / 2 / 1 | Applied | Raw incorrect stand collar/short coat remains; thin dark mask seams and small source patches appear. Constraints do not repair the incorrect garment design. |
| coat_02 | 2026093002 | 2 / 2 / 1 / 2 / 1 | Applied | Raw incorrect stand collar/short coat remains; thin dark mask seams and small source patches appear. Constraints do not repair the incorrect garment design. |
| coat_03 | 2026093001 | 2 / 2 / 1 / 2 / 1 | Applied | Raw incorrect stand collar/short coat remains; thin dark mask seams and small source patches appear. Constraints do not repair the incorrect garment design. |
| coat_03 | 2026093002 | 2 / 2 / 1 / 2 / 1 | Applied | Raw incorrect stand collar/short coat remains; thin dark mask seams and small source patches appear. Constraints do not repair the incorrect garment design. |
| coat_04 | 2026093001 | 2 / 2 / 1 / 2 / 2 | Raw fallback | Parser fallback retains the raw preview: Reference knee-length coat is shortened to a waist-length jacket; required pointed collar is not reproduced. Face, curls, side pose and visible pale skirt retained. |
| coat_04 | 2026093002 | 2 / 2 / 1 / 2 / 2 | Raw fallback | Parser fallback retains the raw preview: Reference knee-length coat is shortened to a waist-length jacket; required pointed collar is not reproduced. Face, curls, side pose and visible pale skirt retained. |
| coat_05 | 2026093001 | 2 / 2 / 1 / 2 / 1 | Applied | Original hair and exposed arms return, but large old pink clothing patches remain in the new garment chest and sleeve regions. Garment construction is broken; mask policy rejected. |
| coat_05 | 2026093002 | 2 / 2 / 1 / 2 / 1 | Applied | Original hair and exposed arms return, but large old pink clothing patches remain in the new garment chest and sleeve regions. Garment construction is broken; mask policy rejected. |
