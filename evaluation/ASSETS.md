# Phase 1 inputs and attribution

Inputs stay in ignored `evaluation/assets/`. The [asset manifest](assets_manifest.json) records exact URLs, dimensions, authors, licenses and SHA-256 hashes. `fetch_assets.py` restores missing inputs and refuses changed bytes. No private user photo participates in the 40-output garment evaluation.

| Files | Source and attribution | License |
|---|---|---|
| `casual_male_portrait.png`, `portrait_model_denim.png`, `urban_man.png`, `coastal_smiling_woman.png`, `clothing_light_blue_denim_shirt.png` | [Comfy-Org/workflow_templates examples](https://github.com/Comfy-Org/workflow_templates/tree/0bfbbbfa260e76f69137f5aa37b7553199c73bc0/input), contributors | Repository MIT license; full notice in [UPSTREAM_LICENSE.txt](UPSTREAM_LICENSE.txt) |
| `plus_size_model.jpg` | **Plus Size Model 1**, [Reba Spike](https://www.flickr.com/photos/161894595@N03/51610395715/), via [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Plus_Size_Model_1.jpg) | [CC BY 2.0](https://creativecommons.org/licenses/by/2.0/) |
| `hoodie_m7agar.jpg` | **Hoodie m7agar**, [YoussefTahoun](https://commons.wikimedia.org/wiki/File:Hoodie_m7agar.jpg) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `tender_denim_jacket.jpg` | **Worn Tender Co. denim jacket**, [Dma132](https://commons.wikimedia.org/wiki/File:Worn_Tender_Co._denim_jacket.jpg) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `jacket_159165.jpg` | **Jacket, 23.225**, [The Metropolitan Museum of Art](https://commons.wikimedia.org/wiki/File:Jacket_MET_23.225_front_CP4.jpg) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `ford_trenchcoat.jpg` | **Trenchcoat worn by President Gerald R. Ford**, [Gerald R. Ford Presidential Museum](https://commons.wikimedia.org/wiki/File:Trenchcoat_worn_by_President_Gerald_R._Ford.jpg); photographer unspecified | Source lists public domain as a US federal work |

The downloaded inputs are unchanged. Generated outputs use local generative AI to alter clothing; they are modified images and do not imply that any pictured person wore, purchased, or endorsed the garment. Retain the Reba Spike attribution, source link, license link and this modification notice with any reuse of her photo or derived previews.

The five people appear in four categories, yielding 20 distinct pairs. There are five garment references: one shirt, one hoodie, two jackets and one coat. This controls subject variation but provides limited garment variety. Four people come from example imagery whose synthetic status is unknown. This engineering benchmark cannot establish representative customer quality or physical fit.
