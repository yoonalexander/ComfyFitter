# ComfyFitter Roadmap

Status: updated 2026-10-04. Local Phases 0-6 are verified for the offered feature scope. Fresh single-garment v4 passed 36/40; guarded source protection passed its matched gate and runtime parity. Hoodie front/detail is qualified. Four rejected outfit studies remain retained; the complete fresh conditional-bag study passed 7/8 for shirt+coat, and its actual browser acceptance passed. Deployment-file preparation and local image builds are complete; live hosted release remains unverified and excluded by the owner's instruction.

Owner decisions, 2026-10-02: original application code uses MIT. No paid services
are authorized; Phase 7 work is deployment-file preparation only. A live hosted
launch remains distinguishable from prepared deployment artifacts. See
[implementation evidence](IMPLEMENTATION_STATUS.md) and
[third-party/model terms](../THIRD_PARTY_NOTICES.md).

## Product and architecture decision

Build a full stack web application that runs locally first. Use React, Vite, TypeScript, and Tailwind CSS for the browser UI; FastAPI, Pydantic, and Pillow for the application backend; SQLite for durable local job records; and the existing ComfyUI installation for GPU inference.

The application provides visual clothing previews, not physical fit or size predictions. Start with one person photo and one upper-body garment reference. Offer only categories that pass the quality gate.

```text
Browser UI -> Local FastAPI backend -> Local ComfyUI -> Local GPU
                  |
                  +-> SQLite job records and temporary image storage
```

The frontend talks only to the application API. The backend owns validation, prompts, workflow mappings, job tracking, and output retrieval. Keep both local services bound to loopback. Use a Vite development proxy and serve the built frontend from the application backend for local distribution.

ComfyUI supports input uploads, queued workflow execution, history lookup, image retrieval, and WebSocket progress updates through its [self-hosted server API](https://docs.comfy.org/development/comfyui-server/comms_routes). The MVP will use that existing API behind a small inference adapter. Browser polling of the application API is sufficient initially; the backend can consume ComfyUI events and reconcile them against history.

### Distribution options

| Option | Where inference runs | Decision |
|---|---|---|
| Local web app | The user's PC | MVP: reuse the existing ComfyUI setup and local GPU |
| Installable desktop app | The user's PC | Optional packaging after Phase 3, when setup friction is measured |
| Hosted web app | A private GPU service | Phase 7, after quality, reliability, and generation cost are known |
| Hosted UI with the user's local GPU | The user's PC through a local companion | Separate optional feature; adds installation, pairing, and connectivity work |

A cloud backend's `127.0.0.1` refers to the cloud server, not the user's PC. Hosting the frontend and backend does not automatically connect them to a user's local ComfyUI. For a fully hosted product, connect the backend to a private GPU worker or a managed inference endpoint. Avoid relying on direct browser access to a local ComfyUI instance.

Desktop packaging should reuse the web UI and Python backend. Select a wrapper and installer only after proving startup, GPU compatibility, model provisioning, and updates. Packaging a UI does not remove ComfyUI's model downloads or hardware requirements.

## Starting point

- The initial repository contained a README and draft design document; no application code.
- The local installation and original saved output are now verified. That output used a single-image int8 coat recolor; the later saved editable graph selects GGUF. It did not prove reference garment transfer.
- Workflow snapshots, pinned model/input hashes, evaluation tools and a licensed 20-pair manifest are now present. See [SETUP.md](SETUP.md) and [the locked protocol](../evaluation/PROTOCOL.md).
- Phase 1 exercises two inputs on the actual GGUF setup. Template support for more references is a later feature and has not been evaluated here.

This roadmap governs milestone scope and acceptance criteria. The [design document](../comfyfitter_design_doc.md) provides architectural background. Its speculative future features are not requirements for the current milestone.

## Milestone order

| Phase | Outcome | Depends on | Status |
|---|---|---|---|
| 0 | Capture and reproduce the existing inference baseline | Access to the local workflow | Complete; MIT app code, research-only model terms documented |
| 1 | Validate complete single-garment transfer | Phase 0 inference baseline | Complete: fresh v4 36/40, 9/10 in every category |
| 2 | Run a reliable generation job through the backend | Phase 1 | Complete: three actual jobs, retrieval/deletion/idempotency and native-execution restart verified |
| 3 | Deliver the local browser MVP | Phase 2 | Complete: actual GPU browser flow, active refresh, download/retry, offline recovery and deletion state verified |
| 4 | Evaluate and add multiple views of one garment | Phase 3 | Complete quality gate: hoodie front/detail enabled; jacket/back/side rejected or unqualified |
| 5 | Reduce unintended edits with spatial constraints | Measured preservation failures | Complete: guarded refinement passed; optional source protection with raw fallback |
| 6 | Support multiple garments and optional saved looks | Reliable single-garment transfer | Complete for offered shirt+coat: fresh quality 7/8 and actual browser acceptance passed; saved looks live-verified |
| 7 | Deliver a hosted service | Phase 3 and a hosting readiness review | Files and access controls prepared; hosted launch excluded by owner |

Phases 4-6 are quality and product extensions; hosting does not require all of them. Phase 5 may move ahead of Phase 4 if preservation failures justify it. Finish and verify the requested phase before starting another.


Checkboxes track implemented or executed work. Completion gates below remain
required: controlled API/browser tests do not satisfy live inference checks, and
rejected full spatial studies do not establish adoption. Hosted work is limited
by the owner to prepared files, with no paid services. See IMPLEMENTATION_STATUS.md.

## Phase 0: Capture the inference baseline

Goal: make the reported local experiment inspectable and repeatable.

- [x] Locate and duplicate the working workflow without modifying the original.
- [x] Save both the editable ComfyUI graph and its API-format export under `workflows/`.
- [x] Record the selected GGUF environment, exact filenames, source revisions, checksums and quantization. The separate recorded int8 reproduction remains outside the garment gate.
- [x] Record GPU, VRAM, image dimensions, prompt, seed, steps, CFG, sampler, scheduler, and any cache or prompt-enhancer settings.
- [x] Run the original coat-color edit with a permitted test image and retain a local evidence record.
- [x] Document setup in `docs/SETUP.md`, including model placement and required nodes. Do not commit model weights or personal photos.
- [x] Add ignore rules for images, generated results, models, local databases, environment files, and caches before adding those assets.
- [x] Resolve the repository license choice before distribution and align the README badge with that choice. MIT applies to original application code; model and input rights remain separate.

Completion gate: another run can load the saved graph and execute the documented baseline successfully. The model identity and dependencies are explicit; required assets have authorized sources. A workflow export and run record are present, with private images kept outside Git.

## Phase 1: Validate single-garment replacement

Goal: prove complete garment replacement before building the application.

- [x] Create a local evaluation manifest with 20 person/garment pairs: five each for shirts, hoodies, jackets, and coats.
- [x] Include variation in body type, skin tone, lighting, and pose, plus occlusion and pattern cases. Use consented or appropriately licensed inputs; record the small dataset's coverage limitations.
- [x] Run each pair with two fixed seeds, for 40 scored outputs. Retain failures as well as successes. Three complete rejected benchmarks and the passing fresh refinement are published.
- [x] Build a baseline upper-body prompt and a distinct outerwear prompt. Record the exact prompt for every output.
- [x] Score identity, body/pose preservation, garment transfer, background/lighting, and artifacts independently.
- [x] Measure cold and warm generation time, resolution, failure rate, and peak VRAM where available on the actual target GPU.
- [x] Save the selected prompt and settings, known limitations, and results in `evaluation/` manifests and `docs/EVALUATION.md`. Selected workflow: [fresh v4 report](EVALUATION_category_reference_v4.md); original report retained unchanged.

Initial scoring rubric: 0 = unacceptable; 1 = usable with noticeable defects; 2 = meets the intended preview quality. A passing output requires identity, body/pose, and garment transfer scores of 2, with background/lighting and artifact scores of at least 1. A coat recolor alone does not count as garment transfer.

Proposed internal gate: at least 32 of 40 outputs pass, and each supported category passes at least 8 of its 10 outputs. These are planning targets, not measured performance or a production accuracy claim. Establish them before evaluation; any revision must explain the changed scope or rubric. Disable categories that fail and record any reduction in launch scope explicitly. T-shirts and sweaters can be added after their own equivalent category checks.

Completion gate: publish the scored local evaluation summary, validated category list, selected workflow, and measured latency/VRAM envelope. If preservation fails repeatedly, investigate prompt or masking improvements before proceeding. Multi-reference experiments are optional here and do not expand MVP scope.

## Phase 2: Backend and ComfyUI integration

Goal: execute the validated workflow through an application API without manually operating ComfyUI.

- [x] Scaffold FastAPI with pinned dependencies, documented configuration, and a configurable ComfyUI base URL.
- [x] Implement a ComfyUI client for uploading images, submitting the API graph, tracking the returned prompt ID, checking history, and retrieving output bytes.
- [x] Keep workflow node/input mappings in a versioned configuration. Copy the graph per job; validate required nodes and inputs before submission.
- [x] Build category-aware prompts from supported inputs. Accept structured application fields rather than arbitrary client-supplied workflows.
- [x] Validate actual image decoding, supported formats, file size, pixel count, and reference count; normalize orientation and strip unnecessary metadata.
- [x] Define a bounded application queue, one active generation initially, durable SQLite job records, and submission idempotency.
- [x] Implement job states, typed errors, configurable execution deadlines, and history reconciliation after backend restarts or event disconnects. Derive deadlines from Phase 1 timings.
- [x] Retrieve results through the application backend. Track every job-owned file in both application and ComfyUI storage.
- [x] Implement explicit deletion and default temporary retention of 24 hours after a terminal state. Run cleanup on startup and periodically, without deleting active-job files or unrelated ComfyUI assets.
- [x] Record the full generation manifest described below.

Initial API contract:

| Endpoint | Behavior |
|---|---|
| `GET /api/health` | Report app health and ComfyUI readiness separately |
| `POST /api/try-on` | Validate inputs and return an accepted job ID |
| `GET /api/try-on/{jobId}` | Return durable status and available progress |
| `GET /api/try-on/{jobId}/result` | Serve completed output bytes; explain missing, pending, or expired results |
| `DELETE /api/try-on/{jobId}` | Delete terminal job assets; reject deletion while the job is active |

States: `queued`, `processing`, `complete`, and `failed`, with a separate asset-expiry field. Store submission intent before contacting ComfyUI; reconcile uncertain submissions before retrying so a transport timeout does not trigger duplicate GPU work. A deadline stops waiting but does not imply inference has stopped: keep tracking any active prompt until completion or a verified stop, and defer its cleanup accordingly.

Per-job cancellation is deferred unless job ownership can be verified. ComfyUI's native interrupt affects the current execution; it must not be treated as an unrestricted cancel-by-job operation on a shared instance.

Verification: unit checks for prompt/reference mapping and graph isolation; API tests for upload rejection and result states; integration tests for offline ComfyUI, invalid graphs, execution errors, transport disconnects, duplicate submissions, restart reconciliation, and cleanup. Mocked tests must be accompanied by at least three consecutive live generations using the saved baseline on the target GPU.

Completion gate: a script can upload one person image and one reference, submit a job, observe a terminal state, retrieve its output, and delete its assets. Error and restart paths behave predictably; repeated submissions do not duplicate inference.

## Phase 3: Local web MVP

Goal: give the validated backend a usable browser interface.

- [x] Build person and garment uploads with previews, removal, validation messages, and guidance for suitable photos.
- [x] Add a selector limited to validated garment categories.
- [x] Show service readiness, queued/processing states, errors, and result expiry. Use stage labels when reliable overall progress is unavailable.
- [x] Prevent accidental duplicate submission and resume job polling after a page refresh.
- [x] Add before/after comparison, result download, and retry with a new seed while reusing available inputs.
- [x] Add explicit deletion and explain local inference and temporary retention. Downloaded files remain under the user's control.
- [x] Support keyboard navigation, accessible labels, and a layout that works in a narrow browser window.
- [x] Provide a Windows launcher that starts the application backend, serves the built UI, opens the browser, and reports whether the existing ComfyUI service is ready.
- [x] Document setup and shutdown. Keep ComfyUI installation and model provisioning explicit prerequisites at this stage.

Completion gate: from the documented setup, a user can launch the app, upload two images, generate a supported garment preview, compare, download, retry, and delete. Run a real browser smoke check against live ComfyUI, including refresh during a job and an offline-service error. Record the hardware and workflow used.

MVP ends here. Accounts, cloud inference, multiple references, persistent look history, masking, and a desktop installer are not Phase 3 requirements.

## Phase 4: Multiple references for one garment

- [x] Add ordered reference roles: front, back, side, and detail.
- [x] Enforce the verified workflow limit, including the person image in the total input count. Five inputs executed, but the qualified hoodie front/detail product mode uses three total inputs.
- [x] Test dynamic image mapping and prompts, including missing optional views.
- [x] Compare one reference with multiple references on matched cases and seeds, measuring fidelity, preservation, latency, and VRAM. Fresh eight-output hoodie-detail study passed with a modest +1 aggregate fine-detail score; median 276.63 seconds. Original jacket-view rejection and failed-quality capacity outputs remain documented in REFERENCE_STUDIES.md.

Completion gate: the evaluation demonstrates a useful fidelity improvement without reducing the Phase 1 preservation pass rate. Document the supported reference limit and tradeoffs; keep one-reference mode available.

## Phase 5: Segmentation and protected regions

- [x] Choose segmentation or masking based on recorded failures, and verify how the exact inference graph accepts spatial constraints.
- [x] Define editable regions and protected face, hair, hands, and unrelated clothing; allow for new garment silhouettes and legitimate occlusion changes.
- [x] Compare constrained and baseline workflows on identical inputs and seeds.
- [x] Measure boundary artifacts, garment fidelity, preservation, latency, and memory.

Completion gate: measured unintended edits decrease without making garment transfer or edge quality unacceptable. Keep a fallback to the validated baseline and document cases where masks perform poorly.

## Phase 6: Multiple garments and optional saved looks

- [x] Introduce explicit garment identity and reference roles, starting with a two-garment combination.
- [x] Evaluate layering, occlusion, independent garment fidelity, and identity preservation with a new test matrix. All eight fresh conditional coat results reviewed; 7/8 passed the unchanged floor. Four earlier rejected studies remain published.
- [x] Add persistent local saved looks only as an explicit opt-in, with deletion and storage limits.

Completion gate: every offered garment combination has documented quality checks. Saved looks survive restart and can be fully deleted. Full outfit mode does not inherit single-garment quality claims automatically.

## Phase 7: Hosted web service

Owner-authorized preparation is complete: pinned private worker/application and
OIDC/TLS gateway files, health/recovery/retention controls, read-only Compose
validation, both local image builds, and 77 Linux backend checks. No paid service,
hosted deployment or registry publication was performed. The unchecked items
below remain requirements for a future live launch; they are not claimed as
verified by local preparation.

- [ ] Benchmark a private GPU worker or managed inference deployment with the actual workflow, custom nodes, and model versions.
- [ ] Choose hosting from measured cold-start time, concurrency, peak memory, cost per generation, and model/license compatibility.
- [x] Add authentication, job and asset ownership checks, bounded worker queues, quotas, and rate limits.
- [x] Add private storage, an explicit retention policy, user deletion, and monitoring across application and inference storage.
- [ ] Add deployment health checks, worker recovery, tracing without photo contents, and enforceable cost limits.
- [ ] Verify that one user cannot retrieve another user's jobs or assets, and that ComfyUI remains inaccessible from the public internet.
- [ ] Test load, worker failure, deployment restarts, and output expiry before launch.

The current [Comfy API v2 documentation](https://docs.comfy.org/api-reference/v2/overview) describes a common jobs/assets interface for managed endpoints and self-hosted ComfyUI through an additional proxy. It is currently beta; re-evaluate it at this phase rather than assuming native local routes and hosted routes are identical. The inference adapter keeps this migration away from the UI.

Completion gate: a user without ComfyUI or a local GPU can complete the MVP flow through the hosted app. Privacy, authorization, failure recovery, throughput, and generation cost meet documented release targets.

## Generation manifest

Record enough information to investigate and rerun a job while its source assets are available:

- Workflow version, graph hash, and immutable job-specific graph snapshot.
- Exact original and effective prompts, prompt-template version, category, and reference order/roles.
- Input hashes and local asset identifiers; dimensions, orientation normalization, and preprocessing version.
- Model filenames, source revisions/checksums, quantization, text encoder, VAE, and custom-node/ComfyUI versions.
- Seed, steps, CFG, sampler, scheduler, denoise settings, output size, cache settings, and any prompt-enhancer configuration.
- GPU/runtime details, submission and execution timestamps, terminal state, output hash, and error code.

Preserve permitted evaluation inputs locally for regression runs; ordinary uploaded photos follow the retention policy. A hash cannot recreate a deleted photo. Do not promise identical pixels across different hardware or dependency versions, and stop claiming rerun availability once required assets expire.

## Initial implementation task (completed)

The initial task was Phase 0: locate the actual working local workflow, capture both exports and its environment, and reproduce the reported experiment. That gate and Phases 1-6 are now verified for the offered scope. Deployment-file preparation is complete. IMPLEMENTATION_STATUS.md records acceptance evidence and future hosted release requirements; the owner has excluded paid services and live deployment.
