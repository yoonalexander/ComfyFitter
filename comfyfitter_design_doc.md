# Virtual Try-On App Design Document

**Status:** Draft v0.1  
**Primary inference backend:** ComfyUI  
**Primary model:** Qwen Image 2.1 Image Edit, GGUF  
**Initial target:** Local desktop development, expandable to hosted GPU inference later

## 1. Project Summary

The project is an AI-powered virtual clothing try-on application. A user uploads a photo of themselves and one or more reference images of a garment. The application uses Qwen Image 2.1 Image Edit through ComfyUI to generate a new image in which the user is wearing the referenced garment while preserving their identity, pose, body proportions, lighting, and background as closely as possible.

The current proof of concept is already functional in ComfyUI. The Qwen Image 2.1 Image Edit template has successfully used a reference image to modify the color of a coat in a user photo.

The first production goal is not precise physical sizing simulation. The goal is visual outfit preview: helping a user understand how the color, style, silhouette, and overall appearance of clothing may look on them.

---

## 2. Goals

### 2.1 Primary Goals

- Allow a user to upload a photo of themselves.
- Allow a user to upload one or more clothing reference images.
- Generate a realistic image of the user wearing the referenced clothing.
- Preserve the user's:
  - face
  - hairstyle
  - skin tone
  - body proportions
  - pose
  - camera angle
  - background
  - lighting
- Preserve important garment characteristics:
  - color
  - pattern
  - fabric appearance
  - fit
  - collar
  - sleeves
  - pockets
  - logos
  - buttons
  - seams
  - other visible design details
- Use the existing Qwen Image 2.1 Image Edit ComfyUI workflow as the initial generation pipeline.
- Keep ComfyUI hidden behind the application backend rather than exposing it directly to users.
- Make the generation workflow replaceable and versioned so it can improve without requiring frontend changes.

### 2.2 Secondary Goals

- Support multiple reference images for the same garment.
- Support multiple garment categories.
- Support full outfit composition.
- Add automated garment and human segmentation.
- Provide multiple generated variations.
- Allow comparison between original and generated images.
- Store previous try-ons locally or in a user account.
- Eventually support remote GPU inference.

---

## 3. Non-Goals

The initial application will not attempt to provide:

- guaranteed clothing size recommendations
- exact garment measurements
- physically accurate fabric simulation
- precise 3D draping
- tailoring recommendations
- body measurement estimation
- guaranteed e-commerce purchase compatibility
- exact prediction of how a specific clothing size will fit in the real world

The generated image should be treated as a visual approximation.

---

## 4. Existing Technical Foundation

The development environment already contains:

- ComfyUI
- a GGUF version of Qwen Image 2.1
- the ComfyUI Qwen Image 2.1 Image Edit template
- a working local inference setup

The existing workflow has already demonstrated reference-based image editing by changing the color of a coat using a supplied image.

This existing workflow should be preserved as the baseline before introducing more complex masking, preprocessing, or postprocessing.

---

## 5. Qwen Image 2.1 Image Edit Workflow

The official ComfyUI Qwen Image 2.1 Image Edit template supports up to 10 image inputs.

The images are referenced directly in the prompt using:

```text
<image1>
<image2>
<image3>
...
<image10>
```

The first image is the image being edited. Additional images are references.

### 5.1 Initial Image Assignment

For the MVP:

| Image | Purpose |
|---|---|
| `<image1>` | User photo and primary edit target |
| `<image2>` | Main garment reference |
| `<image3>` | Optional second garment angle |
| `<image4>` | Optional back view |
| `<image5>` | Optional garment detail or texture |
| `<image6>` | Reserved |
| `<image7>` | Reserved |
| `<image8>` | Reserved |
| `<image9>` | Reserved |
| `<image10>` | Reserved |

The exact mapping should be generated dynamically by the backend based on which assets the user supplies.

### 5.2 Example Prompt

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

Make the garment fit naturally on the person's existing body and pose.
Preserve realistic fabric folds, shadows, occlusion, and interaction with
the person's arms and hair.

Only modify pixels necessary to perform the clothing replacement.
```

The prompt should be constructed programmatically rather than exposing the full prompt to the user.

---

## 6. Product Experience

### 6.1 MVP User Flow

```text
Open application
      |
      v
Upload photo of yourself
      |
      v
Upload clothing image
      |
      v
Select garment category
      |
      v
Click "Try It On"
      |
      v
Generation starts
      |
      v
Preview result
      |
      +----> Generate another variation
      |
      +----> Compare before / after
      |
      +----> Save result
```

### 6.2 Initial Garment Categories

The first version should focus on upper-body clothing because it is easier to constrain and evaluate.

Recommended MVP categories:

- T-shirt
- Shirt
- Sweater
- Hoodie
- Jacket
- Coat

Later versions can add:

- Pants
- Shorts
- Skirts
- Dresses
- Shoes
- Accessories
- Full outfits

---

## 7. Application Architecture

### 7.1 High-Level Architecture

```text
+-------------------------+
|       Frontend          |
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
| Input validation        |
| Image preprocessing     |
| Prompt construction     |
| Workflow configuration  |
| Job management          |
| Security                |
+------------+------------+
             |
             v
+-------------------------+
|        ComfyUI          |
|                         |
| Qwen Image 2.1 Edit     |
| GGUF inference          |
| Workflow execution      |
+------------+------------+
             |
             v
+-------------------------+
|      Generated Image    |
+-------------------------+
```

### 7.2 Recommended Technology Stack

#### Frontend

A suitable stack would be:

- React or Next.js
- TypeScript
- Tailwind CSS
- browser image upload and preview
- before / after comparison component

#### Backend

A suitable stack would be:

- FastAPI
- Python
- Pydantic request models
- Pillow or OpenCV for deterministic image preprocessing where required
- WebSocket or polling integration with ComfyUI

FastAPI is a natural choice because ComfyUI orchestration and image preprocessing can remain in Python.

#### Inference

- ComfyUI
- Qwen Image 2.1 Image Edit
- current GGUF model
- local GPU for development

---

## 8. ComfyUI Integration

The application backend should treat ComfyUI as an internal inference service.

The frontend should never communicate directly with ComfyUI.

### 8.1 Backend Responsibilities

The backend should:

1. Receive the user photo.
2. Receive one or more garment reference images.
3. Validate file type, image dimensions, and file size.
4. Normalize image orientation.
5. Upload or copy input images into the location expected by ComfyUI.
6. Load a versioned API workflow JSON.
7. Replace workflow image inputs.
8. Build the appropriate Qwen prompt.
9. Set generation parameters.
10. Queue the workflow in ComfyUI.
11. Monitor the generation job.
12. Retrieve the generated output.
13. Return the output to the frontend.
14. Clean up temporary files according to the application's retention policy.

### 8.2 Workflow Files

Workflows should be stored as versioned files, for example:

```text
workflows/
  qwen_tryon_upper_v1.json
  qwen_tryon_upper_v2.json
  qwen_tryon_lower_v1.json
  qwen_tryon_full_v1.json
```

This allows experimentation without breaking existing application behavior.

### 8.3 Workflow Configuration

The backend should avoid hardcoding ComfyUI node IDs throughout business logic.

Instead, keep a workflow mapping configuration:

```text
workflow:
  person_image_node: ...
  garment_image_node: ...
  prompt_node: ...
  seed_node: ...
  output_node: ...
```

An even better long-term solution is to assign stable node titles or otherwise build a lightweight abstraction around the exported workflow.

---

## 9. Prompt Construction

Prompt construction should be treated as application logic.

### 9.1 Prompt Components

The final prompt can be composed from:

```text
BASE_IDENTITY_INSTRUCTION
+
GARMENT_CATEGORY_INSTRUCTION
+
REFERENCE_IMAGE_INSTRUCTION
+
PRESERVATION_INSTRUCTION
+
QUALITY_INSTRUCTION
```

### 9.2 Garment-Specific Instructions

#### Upper Body

```text
Replace only the person's upper-body clothing.
Preserve pants, shoes, accessories, face, hair, and background.
```

#### Jacket or Coat

```text
Put the outerwear from the reference images onto the person.
Preserve clothing that would naturally remain visible underneath.
```

#### Lower Body

```text
Replace only the person's lower-body clothing.
Preserve the person's upper-body clothing.
```

#### Full Outfit

```text
Replace the person's outfit with the referenced outfit while preserving
identity, body shape, pose, and environment.
```

### 9.3 Multiple Garment Reference Images

If several images represent the same garment:

```text
<image2> shows the front of the garment.
<image3> shows the back.
<image4> shows a side angle.
<image5> shows close-up material and design details.

Treat all four images as references to the same physical garment.
```

This is one of the strongest reasons to use Qwen Image 2.1's multi-image editing workflow.

---

## 10. Image Input Strategy

### 10.1 User Photo Recommendations

The application should guide users toward images with:

- clear visibility of the relevant body region
- adequate lighting
- sufficient resolution
- limited motion blur
- limited body occlusion
- a useful camera angle for the selected garment
- arms positioned so the garment area can be inferred

For upper-body try-on, a front-facing or slightly angled photo should generally be preferred.

### 10.2 Garment Reference Recommendations

Preferred reference images should have:

- the entire garment visible
- clear colors
- minimal blur
- high enough resolution to show details
- minimal occlusion
- simple or removable backgrounds
- multiple angles when available

Product photos from stores are likely to work especially well because garments are usually isolated and well lit.

---

## 11. Multi-Image Strategy

The 10-image capacity should be treated as an important product feature rather than merely an implementation detail.

### 11.1 Single Garment Mode

```text
<image1> Person
<image2> Garment front
<image3> Garment back
<image4> Garment side
<image5> Fabric/detail view
```

### 11.2 Multi-Garment Outfit Mode

A future full outfit mode could use:

```text
<image1> Person
<image2> Shirt
<image3> Pants
<image4> Jacket
<image5> Shoes
<image6> Accessory
```

Prompt example:

```text
Dress the person in <image1> using the shirt from <image2>, pants from
<image3>, jacket from <image4>, shoes from <image5>, and accessory from
<image6>.
```

This should be tested carefully because model consistency may degrade as the number of independently referenced garments increases.

### 11.3 Reference Priority

The prompt should explicitly state which references have which role.

Do not rely on the model to infer whether two images show:

- the same garment from different angles
- different garments
- style references
- texture references

The application should encode this semantic information into the prompt.

---

## 12. Generation Parameters

The initial implementation should stay close to the working template.

The official Qwen Image 2.1 ComfyUI template currently starts with:

- CFG: 1
- Steps: 25
- Sampler: Euler
- Scheduler: Simple

The template documentation notes that the official Qwen Image 2.1 pipeline commonly uses roughly 40 to 50 Euler steps, while the ComfyUI template begins at 25.

The application should benchmark several configurations rather than immediately maximizing steps.

Recommended test values:

```text
25 steps
35 steps
40 steps
50 steps
```

Evaluate:

- garment accuracy
- identity preservation
- latency
- VRAM usage
- artifact rate

---

## 13. Output Resolution

The first version should prioritize reliability and iteration speed.

A sensible initial target is approximately 1024-class output.

Higher resolutions can be tested after generation quality is stable.

The current Qwen Image 2.1 ComfyUI template supports direct output up to 2K. Because the edit canvas follows the primary image when custom sizing is disabled, the user's source image should remain the main spatial reference.

Avoid changing aspect ratio unnecessarily.

---

## 14. Segmentation and Masking

Masking is not required for the first proof of concept.

However, segmentation is likely to become one of the most important quality improvements.

### 14.1 Problem

Without spatial constraints, a model may unintentionally modify:

- face
- hair
- hands
- body shape
- background
- unrelated clothing
- accessories

### 14.2 Future Pipeline

```text
Person image
     |
     +----> Human parsing / segmentation
     |             |
     |             v
     |       Garment region mask
     |             |
     +-------------+
                   |
                   v
          Qwen Image 2.1 Edit
                   |
                   v
             Final result
```

### 14.3 Category-Aware Masks

Examples:

| Category | Editable Region |
|---|---|
| T-shirt | torso, shoulders, upper arms |
| Hoodie | torso, shoulders, upper arms, neck area |
| Jacket | torso, shoulders, arms |
| Pants | waist, hips, legs |
| Dress | torso, waist, hips, legs |

Hair, hands, and accessories should ideally remain protected unless garment geometry requires occlusion changes.

---

## 15. Identity Preservation

Identity preservation should be measured independently from garment accuracy.

The generated person should continue to resemble the input person.

Preservation priorities:

1. Face
2. Hair
3. Body shape
4. Pose
5. Skin tone
6. Hands
7. Background
8. Lighting

Future techniques may include:

- masks
- face-region protection
- reference consistency prompting
- compositing unchanged image regions back into the final image
- additional identity-reference inputs
- specialized postprocessing

The simplest reliable technique should be preferred over adding unnecessary model complexity.

---

## 16. Garment Fidelity

Garment fidelity measures how closely the generated clothing resembles the supplied reference.

Important properties include:

- base color
- secondary colors
- pattern
- texture
- material
- silhouette
- collar
- sleeve length
- sleeve style
- pockets
- zipper
- buttons
- logos
- printed text
- stitching
- hem
- visible branding

The UI may eventually allow users to mark certain features as especially important.

Example:

```text
Preserve exactly:
[x] Color
[x] Logo
[x] Pattern
[ ] Exact fit
```

This can then alter prompt emphasis.

---

## 17. Handling Logos and Text

Text and logos on clothing are a difficult image-generation problem.

The application should not promise pixel-perfect replication.

Testing should specifically include:

- graphic T-shirts
- sports jerseys
- branded hoodies
- repeating patterns
- small chest logos
- large typography
- embroidered text

If logo fidelity becomes important, future workflows may preserve or composite logos separately.

---

## 18. Seed and Variation Strategy

The application should support controlled variations.

For each generation:

- generate a random seed by default
- store the seed alongside the result
- allow "Try Again"
- optionally allow "Create Variations"
- allow reproducing a result using the same workflow version, prompt, settings, and seed

Stored generation metadata should include:

```json
{
  "workflowVersion": "qwen_tryon_upper_v1",
  "model": "qwen-image-2.1-gguf",
  "seed": 123456789,
  "steps": 25,
  "cfg": 1,
  "garmentType": "jacket",
  "referenceCount": 2
}
```

---

## 19. Frontend Design

### 19.1 Main Screen

```text
+------------------------------------------------+
|                Virtual Try-On                  |
+------------------------------------------------+

  Your Photo

  +----------------------+
  |                      |
  |       Preview        |
  |                      |
  +----------------------+

  Clothing Reference

  +----------------------+
  |                      |
  |       Preview        |
  |                      |
  +----------------------+

  + Add Another Reference

  Garment Type:
  [ Jacket v ]

  [        Try It On        ]

+------------------------------------------------+
```

### 19.2 Results Screen

```text
+------------------------------------------------+
|                   Result                       |
+------------------------------------------------+

        Before        |        After
                      |
        image         |        image

  [ Compare Slider ]

  [ Try Again ] [ Save ] [ New Garment ]

+------------------------------------------------+
```

### 19.3 Generation State

During generation:

- show queued state
- show processing state
- show failure state
- show completion state
- prevent duplicate accidental submissions

A progress indicator can be connected to ComfyUI job progress through WebSocket events where practical.

---

## 20. Backend API Design

Possible API surface:

### Create Try-On

```http
POST /api/try-on
```

Multipart fields:

```text
personImage
garmentImages[]
garmentType
```

Response:

```json
{
  "jobId": "abc123",
  "status": "queued"
}
```

### Get Job Status

```http
GET /api/try-on/{jobId}
```

Response:

```json
{
  "jobId": "abc123",
  "status": "processing",
  "progress": 0.62
}
```

### Get Result

```http
GET /api/try-on/{jobId}/result
```

Response:

```json
{
  "jobId": "abc123",
  "status": "complete",
  "imageUrl": "/generated/abc123.png"
}
```

For a local-only MVP, these endpoints can be simplified.

---

## 21. Job Management

Image generation is slower than a typical HTTP request.

The backend should treat each generation as a job.

Possible states:

```text
uploaded
queued
processing
complete
failed
cancelled
```

Each job should store:

- job ID
- ComfyUI prompt ID
- creation time
- workflow version
- model configuration
- input asset paths
- status
- output path
- error message if applicable

---

## 22. Privacy and Security

User photographs are sensitive data.

The application should minimize collection and retention.

### 22.1 Local MVP

For a local application:

- keep all images on the user's machine
- do not transmit images to external services
- clearly indicate that inference is local
- automatically clean temporary files where practical

### 22.2 Hosted Version

If hosted later:

- use encrypted transport
- restrict access to input and output files
- generate unguessable file identifiers
- implement automatic deletion
- define an explicit retention period
- avoid permanent storage by default
- never expose ComfyUI directly to the public internet
- validate all uploaded files
- enforce maximum upload sizes
- authenticate generation requests
- rate-limit users
- prevent arbitrary workflow submission
- sanitize filenames

ComfyUI should sit on a private internal network behind the application API.

---

## 23. Error Handling

The application should handle:

### User Input Errors

- unsupported file type
- corrupted image
- image too small
- image too large
- no visible person
- no garment reference
- too many reference images

### Inference Errors

- out of memory
- model unavailable
- ComfyUI offline
- generation cancelled
- invalid workflow
- missing ComfyUI node
- output not created

### Quality Failures

A technically successful generation may still be visually unacceptable.

The UI should therefore always make retrying easy.

---

## 24. Evaluation Framework

Quality should be evaluated systematically rather than only by subjective impressions.

Build a small internal test dataset containing different:

- body types
- genders
- skin tones
- hairstyles
- poses
- camera angles
- backgrounds
- garment types
- garment colors
- garment patterns
- garment materials

### 24.1 Evaluation Dimensions

Score each result separately for:

1. Identity preservation
2. Garment color accuracy
3. Garment shape accuracy
4. Garment detail accuracy
5. Pose preservation
6. Body preservation
7. Background preservation
8. Lighting consistency
9. Realism
10. Visible artifacts

### 24.2 Test Matrix

Example:

| Test | Person Pose | Garment | References |
|---|---|---|---:|
| A | Front | T-shirt | 1 |
| B | Front | Jacket | 1 |
| C | Front | Jacket | 3 |
| D | 3/4 pose | Hoodie | 2 |
| E | Arms crossed | Coat | 2 |
| F | Side pose | Jacket | 3 |

This will show whether multiple reference images actually improve garment fidelity.

---

## 25. Benchmarking

Every major workflow revision should record:

- GPU
- model quantization
- workflow version
- image resolution
- step count
- sampler
- generation time
- peak VRAM if measurable
- output quality scores

This makes it possible to answer whether a more complex workflow is actually worth its computational cost.

---

## 26. Development Phases

### Phase 0: Existing Proof of Concept

Already achieved:

- ComfyUI installed
- Qwen Image 2.1 GGUF installed
- official Image Edit template working
- reference-based coat color editing validated

### Phase 1: Manual Virtual Try-On

Goal:

Prove garment replacement works reliably in ComfyUI before building the application.

Tasks:

- test shirts
- test hoodies
- test jackets
- test coats
- test single garment reference
- test multiple garment references
- develop initial prompt template
- determine baseline generation settings
- collect failures

Success criterion:

A useful percentage of controlled test images produce recognizable garment transfer while keeping the person visually consistent.

### Phase 2: ComfyUI API Integration

Goal:

Run the same workflow without manually using the ComfyUI interface.

Tasks:

- export API workflow
- identify dynamic input nodes
- upload user image
- upload garment images
- inject prompt
- submit workflow
- track job
- retrieve output
- save generation metadata

### Phase 3: Local Web Application

Goal:

Provide a usable interface around local ComfyUI.

Features:

- person image upload
- garment image upload
- garment category
- generate button
- generation status
- result preview
- before / after view
- retry
- local history

### Phase 4: Multi-Reference Try-On

Goal:

Improve garment accuracy.

Features:

- multiple garment images
- image role selector:
  - front
  - back
  - side
  - detail
- dynamic prompt generation
- multi-reference benchmarking

### Phase 5: Automatic Segmentation

Goal:

Reduce unintended edits.

Features:

- detect person
- segment clothing/body regions
- generate category-aware mask
- preserve non-target regions
- benchmark identity preservation before and after masking

### Phase 6: Full Outfit Support

Goal:

Combine independent garment references.

Possible mapping:

```text
<image1> user
<image2> shirt
<image3> pants
<image4> jacket
<image5> shoes
```

This phase should only begin once single-garment transfer is reliable.

### Phase 7: Hosted Service

Goal:

Run the application without requiring users to install ComfyUI.

Requirements:

- GPU server
- private ComfyUI service
- job queue
- authentication
- storage lifecycle
- rate limiting
- privacy policy
- abuse prevention
- observability
- cost controls

---

## 27. Suggested Repository Structure

```text
virtual-try-on/
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
+-- tests/
|   +-- workflow/
|   +-- prompts/
|   +-- api/
|
+-- evaluation/
|   +-- cases/
|   +-- results/
|   +-- benchmarks/
|
+-- docs/
|   +-- DESIGN.md
|
+-- README.md
```

---

## 28. Core Backend Modules

### `ComfyUIClient`

Responsible for communication with ComfyUI.

Possible interface:

```python
class ComfyUIClient:
    def upload_image(self, image_path): ...
    def queue_prompt(self, workflow): ...
    def get_history(self, prompt_id): ...
    def get_result(self, prompt_id): ...
```

### `WorkflowBuilder`

Responsible for turning a workflow template into a job-specific workflow.

```python
class WorkflowBuilder:
    def set_person_image(self, image): ...
    def set_reference_images(self, images): ...
    def set_prompt(self, prompt): ...
    def set_seed(self, seed): ...
    def build(self): ...
```

### `TryOnPromptBuilder`

Responsible for prompt creation.

```python
class TryOnPromptBuilder:
    def build(
        self,
        garment_type,
        reference_roles,
        preserve_background=True,
        preserve_identity=True
    ): ...
```

Keeping these responsibilities separate will make workflow experimentation much easier.

---

## 29. Workflow Versioning

Every output should be reproducible from metadata.

A workflow version should change whenever generation behavior changes materially.

Example:

```text
qwen_tryon_upper_v1
qwen_tryon_upper_v2_masked
qwen_tryon_upper_v3_multiref
```

Store the workflow version with every generated result.

This is useful for:

- debugging
- comparing model behavior
- evaluating improvements
- reproducing good outputs
- rolling back regressions

---

## 30. Future Opportunities

Once virtual try-on is reliable, the same platform could support:

### Outfit Builder

Users combine multiple garments and generate a complete look.

### Closet

Users upload clothing they already own.

### Saved Looks

Users save generated outfits.

### Outfit Comparison

Generate multiple garments against the same source photo and compare them.

### Shopping Integration

Import product images from a retailer or product URL.

### Style Recommendations

Recommend combinations from a user's saved closet.

### Batch Try-On

Try the same person photo against many garments.

```text
Person + Jacket A
Person + Jacket B
Person + Jacket C
Person + Jacket D
```

### Model Comparison

The workflow abstraction could eventually allow different image-editing models to compete behind the same application interface.

---

## 31. Major Technical Risks

### Identity Drift

The model changes the user's face or body.

**Mitigation:** stronger prompting, masking, compositing, identity references.

### Garment Drift

The output looks like a similar garment rather than the specific reference.

**Mitigation:** multiple reference images, explicit prompts, improved preprocessing.

### Pose Problems

Complex poses create malformed sleeves or garment geometry.

**Mitigation:** user photo guidance, segmentation, model improvements.

### Occlusion

Hands, hair, bags, and accessories interact incorrectly with clothing.

**Mitigation:** segmentation and protected regions.

### Text and Logo Corruption

Brand names or graphics are changed.

**Mitigation:** detect affected use cases, test specialized preservation approaches.

### Performance

High-resolution generations may be slow on consumer GPUs.

**Mitigation:** benchmark resolution, steps, quantization, and staged previews.

### VRAM Limitations

Some workflows may not fit available hardware.

**Mitigation:** GGUF quantization, model offloading, lower resolution, optimized workflow design.

---

## 32. MVP Definition

The MVP is complete when a user can:

1. Open the application.
2. Upload one photo of themselves.
3. Upload one clothing reference image.
4. Select an upper-body garment category.
5. Click "Try It On."
6. Have the backend automatically execute the Qwen Image 2.1 Image Edit ComfyUI workflow.
7. Receive a generated result.
8. Compare it to the original.
9. Retry with a new seed.

The MVP does not require masking, accounts, cloud inference, multiple garments, or exact sizing.

---

## 33. Immediate Next Steps

1. Duplicate the existing working Qwen Image 2.1 Image Edit workflow.
2. Save it specifically as the project's baseline try-on workflow.
3. Test complete garment replacement rather than only color replacement.
4. Test one reference image versus two, three, and four reference images.
5. Create a standard upper-body prompt.
6. Build a small evaluation set.
7. Record successful and unsuccessful generations.
8. Export the stable workflow in API format.
9. Build the backend ComfyUI client.
10. Create the minimal upload and result UI.
11. Add segmentation only after the baseline workflow has measurable limitations.

---

## 34. Reference Workflow Facts

The current official ComfyUI Qwen Image 2.1 Image Edit template provides:

- image inputs from `image_1` through `image_10`
- `<image1>` through `<image10>` prompt references
- `image_1` as the primary edit target
- additional images as references
- default template values including CFG 1, 25 steps, Euler sampler, and Simple scheduler
- support for a primary image-driven canvas and optional custom resolution
- direct output support up to 2K according to the template notes

Official template:

https://github.com/Comfy-Org/workflow_templates/blob/main/templates/image_qwen_image_2_1_image_edit.json

ComfyUI documentation:

https://docs.comfy.org/

---

## 35. Design Principle

The application should keep three concerns independent:

```text
Product UI
    |
    v
Try-On Application Logic
    |
    v
Versioned ComfyUI Workflow
    |
    v
Image Model
```

The frontend should not depend on Qwen-specific node IDs.

The backend should not assume that the current workflow will remain permanent.

ComfyUI should remain an interchangeable inference layer.

This separation makes it possible to improve prompts, swap workflows, introduce masks, upgrade Qwen versions, or replace the model entirely without redesigning the product.
