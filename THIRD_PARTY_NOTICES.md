# Third-party notices

ComfyFitter's original application code is licensed under [MIT](LICENSE), selected
by the owner on 2026-10-02. That license does not relicense model weights, external
services, dependencies, benchmark photos, or generated derivatives of those photos.

## Workflow templates and example assets

Workflow snapshots were adapted from the ComfyUI/Qwen template environment;
person/garment example inputs originate from
[Comfy-Org/workflow_templates](https://github.com/Comfy-Org/workflow_templates/tree/0bfbbbfa260e76f69137f5aa37b7553199c73bc0).
Preserve the full upstream [MIT notice](evaluation/UPSTREAM_LICENSE.txt).
Changes include API export, removal of a non-generation comparison node, two-input
mapping, and category prompts. Original private photos and model weights are not
distributed in this repository.

Other benchmark inputs carry individual CC0, CC BY 2.0, or public-domain notices.
See [evaluation/ASSETS.md](evaluation/ASSETS.md) and the immutable source/hash
manifest. Reused Reba Spike imagery and its modified previews need the attribution,
source/license links, and modification notice specified there.

## Qwen Image 2.1 model

Checked 2026-10-02 against the official
[Qwen Research License Agreement](https://huggingface.co/Qwen/Qwen-Image-2.1/blob/main/LICENSE)
and [upstream source license](https://github.com/QwenLM/Qwen-Image-2.1/blob/main/LICENSE).
The current model grant is limited to research/evaluation use. Commercial use
requires a separate agreement from the model owner. A free public service should
not be assumed to qualify solely because users do not pay; its intended use must
also meet the research/evaluation restriction.

The GGUF conversion, encoder, and VAE sources/hashes are recorded in
[evaluation/environment.json](evaluation/environment.json). Their presence on disk
and this application's MIT license do not establish permission for an unrestricted
production service. Local work here is development and evaluation. Deployment
files must retain that restriction and must not download or redistribute weights
automatically. A release that redistributes Qwen materials must include the
agreement, required `Notice` attribution, and notices of modifications. This
repository currently distributes no weights and no model code.

ComfyUI and custom nodes are separate prerequisites with their own upstream
licenses. Packaging/distribution must inventory the actual dependency artifacts;
the application license does not cover them.

## Windows desktop window dependencies

The desktop window installs pywebview 6.2.1 (BSD-3-Clause), pythonnet 3.2.0
(MIT), clr_loader 0.3.1 (MIT), Bottle 0.13.4 (MIT), and proxy_tools 0.1.0
(MIT). These dependencies are separate from the original MIT application code.
Their installed packages retain upstream license notices. The current desktop
setup reuses this checkout and the pre-existing ComfyUI/model installation;
it does not bundle or redistribute the model weights. A future standalone
installer must retain the dependency notices and review WebView2 distribution
requirements. See [desktop setup](docs/DESKTOP.md).

## Optional local segmentation investigation

The protected-region experiment uses
[mattmdjaga/segformer_b2_clothes](https://huggingface.co/mattmdjaga/segformer_b2_clothes/tree/584abc1e1d260e23c0fc627c5217a09b2b461046)
at that pinned revision. Its model card points to the
[NVIDIA Source Code License for SegFormer](https://github.com/NVlabs/SegFormer/blob/master/LICENSE),
whose use limitation restricts use to research/evaluation. This is a separate
local research dependency, not MIT-licensed application content. Weights remain
in ignored `.local/models/`, are not redistributed, and are loaded as safetensors
without remote model code. Exact hashes are recorded in
[segmentation_environment.json](evaluation/segmentation_environment.json).
