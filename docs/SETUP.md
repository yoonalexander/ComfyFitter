# Captured local inference setup

Captured 2026-09-30 on Windows, RTX 5060 (8,151 MiB reported VRAM), NVIDIA driver 591.86. [environment.json](../evaluation/environment.json) records checksums and runtime versions: ComfyUI 0.37.2 at `830232b856045ca2892833212d7771078a13edd5`, Python 3.13.12, Torch 2.12.1+cu130, Pillow 12.3.0, ComfyUI-GGUF 1.1.10 / gguf 0.19.0. Existing dependencies and weights were reused without upgrades.

This installation was found at:

```text
C:\Users\Admin\AppData\Local\Comfy-Desktop\ComfyUI-Installs\ComfyUi\ComfyUI
```

Use its `.venv\Scripts\python.exe`. Launching the adjacent standalone Python directly lacks the environment's Torch dependency.

| Component | Relative model path | Role |
|---|---|---|
| Diffusion model | `models/unet/qwen_image_2.1_Q4_K_M.gguf` | Locked Phase 1 GGUF candidate, Q4_K_M |
| Text encoder | `models/text_encoders/qwen3vl_8b_w4a8.safetensors` | Existing W4A8 encoder |
| VAE | `models/vae/qwen_image_2.1_vae_bf16.safetensors` | BF16 VAE |
| Alternative model | `models/diffusion_models/qwen_image_2.1_int8_convrot.safetensors` | Recorded original recolor only; excluded from Phase 1 gate |

The GGUF loader requires `custom_nodes/ComfyUI-GGUF`. The captured ComfyUI provides the Qwen 2.1 encode/cache, switch, resolution and advanced-save nodes used in this graph. Older installations may lack them. The installed GGUF, encoder and VAE hashes match the published LFS hashes at the source revisions in [environment.json](../evaluation/environment.json): [Abiray/Qwen-Image-2.1-GGUF](https://huggingface.co/Abiray/Qwen-Image-2.1-GGUF/tree/c9dd12108f53974cd1e0abd708df042d6df0ca8d) and [Comfy-Org/Qwen-Image-2.1](https://huggingface.co/Comfy-Org/Qwen-Image-2.1/tree/cb504a4090723e43f17ad01cec0359490e2de613). This identifies the binary contents, not their historical download origin. Source metadata names the Qwen research license; deployment and redistribution require the separate license review already scheduled in the roadmap. The owner selected MIT for original application code on 2026-10-02; model and benchmark licenses remain separate. See [third-party notices](../THIRD_PARTY_NOTICES.md).

## Isolated server

From the repository root, create `.local/input`, `.local/output`, `.local/user` and use an unused loopback port. The evaluation scripts currently default to 8188. Do not run a second server on an occupied port.

```powershell
$comfyRoot = 'C:\Users\Admin\AppData\Local\Comfy-Desktop\ComfyUI-Installs\ComfyUi\ComfyUI'
$projectRoot = (Get-Location).Path
$evaluationPython = Join-Path $comfyRoot '.venv\Scripts\python.exe'
New-Item -ItemType Directory -Force -Path '.local/input', '.local/output', '.local/user' | Out-Null
Push-Location $comfyRoot
& $evaluationPython main.py --listen 127.0.0.1 --port 8188 --disable-auto-launch --input-directory "$projectRoot\.local\input" --output-directory "$projectRoot\.local\output" --user-directory "$projectRoot\.local\user"
Pop-Location
```

The foreground command keeps its terminal busy; run evaluation commands in another terminal. Ctrl+C shuts down this dedicated server after its queue is idle. Keep it bound to loopback. Do not interrupt or unload models on an unrelated shared server.

## Workflow snapshots

- [qwen_edit_saved_gguf.ui.json](../workflows/qwen_edit_saved_gguf.ui.json): sanitized editable saved graph; replace placeholder input images. It preserves the original one-image recolor configuration and is not the Phase 1 two-image API graph.
- [qwen_coat_recolor_recorded_int8.api.json](../workflows/qwen_coat_recolor_recorded_int8.api.json): actual original executed graph recovered from saved PNG metadata. Uses one input and int8, proving a recolor rather than reference transfer.
- [qwen_tryon_upper_candidate_gguf.api.json](../workflows/qwen_tryon_upper_candidate_gguf.api.json): tested two-image candidate; the runner injects category prompt, two uploaded names and seed.

Image-comparison UI node 472 was removed from API graphs because its empty-string compare inputs fail API validation. This does not participate in generation. Pristine copies, source personal photo and recolor smoke outputs are local under ignored `.local/`. Personal assets are not committed.

The two recolor reproductions succeeded: original int8 server execution 113.113 seconds; GGUF 195.066 seconds. They differ in model, cache state and image resolution from the Phase 1 benchmark, so they are not a controlled speed comparison or garment-transfer evidence.

Phase 1 locks 25 steps, CFG 1, Euler/simple, denoise 1, aspect-preserving pixel budget 1024, batch 1, no enhancer or masking, and the existing Qwen cache node. Exact job graphs and outputs remain under ignored `evaluation/results/`. See [evaluation instructions](../evaluation/README.md) for the fixed inputs and scoring protocol.
