<div align="center">

# ComfyFitter

AI-powered virtual clothing try-on using **ComfyUI** and **Qwen Image 2.1 Image Edit**.

[![Python][python-shield]][python-url]
[![ComfyUI][comfyui-shield]][comfyui-url]
[![Qwen Image 2.1][qwen-shield]][qwen-url]
[![Project Status][status-shield]][repo-url]
[![GitHub Stars][stars-shield]][stars-url]
[![GitHub Issues][issues-shield]][issues-url]
[![GitHub License][license-shield]][license-url]

</div>

The goal of this project is to let a user upload a photo of themselves, provide one or more clothing reference images, and generate a realistic preview of how that clothing could look on them while preserving their identity, pose, body proportions, lighting, and background as closely as possible.

> ComfyFitter is intended for visual outfit preview, not exact physical sizing or garment fit prediction.

---

## Current Status

The project is currently in the proof-of-concept and workflow validation stage.

The current setup includes:

- ComfyUI installed locally
- Qwen Image 2.1 running through a GGUF model
- the Qwen Image 2.1 Image Edit ComfyUI template
- successful reference-based clothing edits
- support for up to 10 image inputs
- prompt-level image references using `<image1>` through `<image10>`

A basic test has already successfully changed the color of a coat in a user image using a reference image.

---

## Core Idea

The initial workflow uses:

```text
<image1> = photo of the user
<image2> = clothing reference
<image3> = optional second garment angle
<image4> = optional back view
<image5> = optional detail or texture reference
```

The model is then prompted to preserve the person while replacing the relevant clothing.

Example:

```text
Keep the person, identity, facial features, hairstyle, body shape, pose,
camera angle, background, and lighting in <image1> unchanged.

Replace the person's current upper-body clothing with the garment shown
in <image2>.

Use <image3> and <image4> as additional references for the same garment
when available.

Reproduce the garment accurately, including its color, fabric, pattern,
collar, sleeves, seams, pockets, buttons, logos, proportions, and visible
design details.

Only modify what is necessary to perform the clothing replacement.
```

---

## Planned User Flow

```text
Upload photo of yourself
        |
        v
Upload clothing reference
        |
        v
Select garment type
        |
        v
Click "Try It On"
        |
        v
Qwen Image 2.1 runs through ComfyUI
        |
        v
View generated result
        |
        +--> Try another variation
        +--> Compare before / after
        +--> Save result
```

---

## MVP Scope

The first version will focus on upper-body clothing:

- T-shirts
- shirts
- sweaters
- hoodies
- jackets
- coats

The MVP will support:

- one user image
- one primary clothing reference
- optional extra garment reference images
- garment type selection
- AI generation
- before / after comparison
- retry with a different seed

The MVP will not attempt to provide exact sizing recommendations.

---

## Architecture

```text
+-------------------------+
|        Frontend         |
|                         |
| Upload person image     |
| Upload garment images   |
| Select garment type     |
| Generate / compare      |
+------------+------------+
             |
             v
+-------------------------+
|      Application API    |
|                         |
| Validation              |
| Prompt construction     |
| Workflow configuration  |
| Job management          |
+------------+------------+
             |
             v
+-------------------------+
|         ComfyUI         |
|                         |
| Qwen Image 2.1 Edit     |
| GGUF inference          |
+------------+------------+
             |
             v
+-------------------------+
|      Generated Image    |
+-------------------------+
```

---

## Suggested Stack

### Frontend

- React or Next.js
- TypeScript
- Tailwind CSS

### Backend

- FastAPI
- Python
- Pydantic
- Pillow or OpenCV for preprocessing where needed

### AI / Inference

- ComfyUI
- Qwen Image 2.1 Image Edit
- GGUF model
- local GPU during development

---

## Why ComfyUI

ComfyUI provides a useful separation between the application and the image generation pipeline.

The app can:

1. upload input images
2. load a saved workflow
3. inject image paths and prompts
4. submit the workflow to ComfyUI
5. track generation progress
6. retrieve the generated image

This keeps the frontend independent from the actual node graph.

The workflow can evolve without requiring major frontend changes.

---

## Multi-Image Support

Qwen Image 2.1 Image Edit can accept up to 10 input images.

This can be used for multiple views of the same garment.

Example:

```text
<image1> Person
<image2> Garment front
<image3> Garment back
<image4> Garment side
<image5> Fabric detail
```

A future full-outfit mode could use separate references:

```text
<image1> Person
<image2> Shirt
<image3> Pants
<image4> Jacket
<image5> Shoes
```

The prompt should always explicitly explain the role of each image.

---

## Workflow Versioning

ComfyUI workflows should be stored separately and versioned.

Example:

```text
workflows/
  qwen_tryon_upper_v1.json
  qwen_tryon_upper_v2.json
  qwen_tryon_lower_v1.json
  qwen_tryon_full_v1.json
```

Each generated result should record which workflow version created it.

This allows:

- reproducibility
- A/B testing
- easier debugging
- rollback
- workflow benchmarking

---

## Suggested Repository Structure

```text
comfyfitter/
|
+-- frontend/
|   +-- src/
|       +-- components/
|       +-- pages/
|       +-- api/
|       +-- types/
|
+-- backend/
|   +-- app/
|       +-- api/
|       +-- comfyui/
|       |   +-- client.py
|       |   +-- workflow.py
|       |   +-- jobs.py
|       +-- prompts/
|       |   +-- try_on.py
|       +-- preprocessing/
|       +-- models/
|       +-- services/
|
+-- workflows/
|   +-- qwen_tryon_upper_v1.json
|   +-- qwen_tryon_lower_v1.json
|   +-- qwen_tryon_full_v1.json
|
+-- evaluation/
|   +-- cases/
|   +-- results/
|   +-- benchmarks/
|
+-- docs/
|   +-- DESIGN.md
|
+-- tests/
|
+-- README.md
```

---

## Local Development

### Requirements

- Windows, Linux, or macOS
- ComfyUI
- a supported GPU
- Qwen Image 2.1 GGUF model
- Python 3.10+
- Node.js if using the planned web frontend

### 1. Start ComfyUI

Run ComfyUI normally and verify that the Qwen Image 2.1 Image Edit template works.

By default, a local ComfyUI instance typically runs at:

```text
http://127.0.0.1:8188
```

### 2. Validate the Base Workflow

Before integrating the application:

- load the Qwen Image 2.1 Image Edit template
- set `<image1>` to a person image
- set `<image2>` to a garment reference
- test garment replacement manually
- save a stable workflow
- export the workflow in API format

### 3. Connect the Backend

The backend will eventually:

```text
Receive user images
      |
      v
Upload images to ComfyUI
      |
      v
Load workflow JSON
      |
      v
Inject images + prompt + seed
      |
      v
Queue workflow
      |
      v
Wait for completion
      |
      v
Return generated result
```

---

## Prompt Strategy

Prompt construction should be part of the backend rather than hardcoded in the UI.

The generated prompt should describe:

- which image contains the user
- which images contain garment references
- which clothing region should change
- what must remain unchanged
- which garment details should be preserved

Different garment categories should use different prompt templates.

For example:

```text
upper-body clothing
lower-body clothing
outerwear
full outfit
```

---

## Future Segmentation

The first version can rely on prompt-only editing.

A later version should add segmentation or masking to reduce unintended changes.

Potential pipeline:

```text
Person image
     |
     +--> Human parsing / segmentation
     |          |
     |          v
     |    Garment region mask
     |          |
     +----------+
                |
                v
        Qwen Image 2.1 Edit
                |
                v
          Final result
```

This should help preserve:

- face
- hair
- hands
- background
- unrelated clothing
- accessories

---

## Evaluation

The project should be evaluated on separate dimensions:

1. identity preservation
2. garment color accuracy
3. garment shape accuracy
4. garment detail accuracy
5. pose preservation
6. body preservation
7. background preservation
8. lighting consistency
9. realism
10. visible artifacts

A small internal test set should include:

- different body types
- different skin tones
- different poses
- different camera angles
- different garment types
- simple and complex patterns
- different lighting conditions

---

## Known Challenges

### Identity Drift

The model may unintentionally alter the user's face, body, or hair.

### Garment Drift

The generated garment may resemble the reference without matching it exactly.

### Occlusion

Hands, hair, bags, and accessories can make garment replacement harder.

### Logos and Text

Text and brand graphics may be distorted.

### Complex Poses

Crossed arms, side poses, or partially hidden clothing can reduce quality.

### Performance

High-resolution image editing can be slow and VRAM intensive.

---

## Roadmap

### Phase 0
- [x] Install ComfyUI
- [x] Install Qwen Image 2.1 GGUF
- [x] Run Image Edit template
- [x] Validate basic clothing edit

### Phase 1
- [ ] Test full garment replacement
- [ ] Test multiple garment categories
- [ ] Test multiple reference images
- [ ] Establish prompt baseline
- [ ] Build evaluation set

### Phase 2
- [ ] Export stable ComfyUI API workflow
- [ ] Build ComfyUI Python client
- [ ] Inject dynamic images and prompts
- [ ] Queue workflows programmatically
- [ ] Retrieve generated output

### Phase 3
- [ ] Build local web UI
- [ ] Add image upload
- [ ] Add garment category selector
- [ ] Add before / after comparison
- [ ] Add retry generation

### Phase 4
- [ ] Add multi-reference garment support
- [ ] Add reference-role selection
- [ ] Benchmark multi-image fidelity

### Phase 5
- [ ] Add human parsing / segmentation
- [ ] Add category-aware masks
- [ ] Improve identity preservation

### Phase 6
- [ ] Add full outfit generation
- [ ] Add multiple garment references
- [ ] Add saved looks and history

### Phase 7
- [ ] Add hosted GPU inference
- [ ] Add authentication
- [ ] Add storage lifecycle
- [ ] Add rate limiting
- [ ] Add privacy protections

---

## Privacy

User photos should be treated as sensitive data.

For the local version:

- keep inference local
- avoid external image transmission
- minimize temporary storage
- clean up temporary files

For a future hosted version:

- use encrypted connections
- use private object storage
- use unguessable file identifiers
- automatically delete images after a defined retention period
- never expose ComfyUI directly to the public internet
- validate uploads
- enforce file-size limits
- authenticate generation requests
- rate-limit access

---

## Limitations

This project generates a visual approximation.

It does not currently know:

- exact body measurements
- garment measurements
- fabric elasticity
- fabric weight
- garment construction
- exact 3D body geometry
- exact physical draping

A generated result should therefore not be treated as proof that a specific size will fit.

---

## Design Document

A more detailed technical design is available in:

```text
docs/DESIGN.md
```

It covers:

- workflow design
- prompt generation
- backend API structure
- job management
- masking
- evaluation
- workflow versioning
- security
- benchmarking
- development phases

---

## Long-Term Vision

The project can eventually become more than a single-garment try-on tool.

Possible future features include:

- virtual closet
- saved outfits
- outfit comparison
- batch try-on
- retailer product import
- outfit recommendations
- multi-garment composition
- style discovery
- model and workflow comparison

The core architecture should remain modular so that Qwen Image 2.1, ComfyUI workflows, segmentation models, and future image-editing models can evolve independently from the product UI.

---

## Badge References

[python-shield]: https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat&logo=python&logoColor=white
[python-url]: https://www.python.org/

[comfyui-shield]: https://img.shields.io/badge/ComfyUI-000000?style=flat
[comfyui-url]: https://github.com/comfyanonymous/ComfyUI

[qwen-shield]: https://img.shields.io/badge/Qwen-Image%202.1-6C5CE7?style=flat
[qwen-url]: https://huggingface.co/Qwen

[status-shield]: https://img.shields.io/badge/status-in%20development-orange?style=flat
[repo-url]: https://github.com/yoonalexander/ComfyFitter

[stars-shield]: https://img.shields.io/github/stars/yoonalexander/ComfyFitter?style=flat&logo=github
[stars-url]: https://github.com/yoonalexander/ComfyFitter/stargazers

[issues-shield]: https://img.shields.io/github/issues/yoonalexander/ComfyFitter?style=flat&logo=github
[issues-url]: https://github.com/yoonalexander/ComfyFitter/issues

[license-shield]: https://img.shields.io/github/license/yoonalexander/ComfyFitter?style=flat
[license-url]: https://github.com/yoonalexander/ComfyFitter/blob/main/LICENSE
