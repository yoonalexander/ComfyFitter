# Local application backend

2026-10-03. The API, durable worker, readiness/recovery and isolation controls are
implemented. Three consecutive live application generations, owned restart,
retrieval and deletion have passed; see [live acceptance](LIVE_ACCEPTANCE.md).
The complete passing v4 workflow enables the four evaluated categories.

## Setup and launch

Use a separate application environment. Leave the existing ComfyUI environment
and model installation intact. From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements-lock.txt
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --workers 1 --no-access-log
```

`requirements-lock.txt` captures the tested application and test dependencies.
`requirements.txt` lists the direct runtime dependencies; it does not pin every
transitive package. This is separate from the inference environment in SETUP.md.
The current Starlette TestClient emits a deprecation warning for httpx, but the
API checks pass. No automatic telemetry exporter is configured.

ComfyUI must use the dedicated input/output directories documented in SETUP.md.
The application can contact a configurable HTTP service, but filesystem cleanup
and PNG recovery require access to that service's configured storage directories.
A remote worker needs shared private mounts or a storage adapter before deployment.
Run one application process per storage directory. An OS-held lock prevents a
second worker; its file can remain after shutdown without holding the lock.
Ctrl+C stops the application, while ComfyUI continues any submitted inference.

## Configuration

Environment variables use the `COMFYFITTER_` prefix. The application reads the
process environment; it does not automatically load an `.env` file.

| Suffix | Default | Meaning |
|---|---|---|
| `DATA_DIR` | `.local/app` under this checkout | SQLite and temporary job folders |
| `COMFY_URL` | `http://127.0.0.1:8188` | Inference service, without embedded credentials |
| `COMFY_INPUT_DIR` | `.local/input` | Actual upstream input directory |
| `COMFY_OUTPUT_DIR` | `.local/output` | Actual upstream output directory |
| `QUALITY_MANIFEST` | `evaluation/summary_category_reference_v4.json` | Passed selected-workflow report |
| `FEATURE_MANIFEST` | `evaluation/feature_quality.json` | Separate matched reference/outfit qualification; disabled until passed |
| `PROTECTION_MANIFEST` | `evaluation/summary_semantic_guarded_v5.json` | Separate full protection study and actual CPU runtime parity |
| `PROTECTION_PYTHON` | empty | Explicit existing local pinned CPU-parser interpreter; empty keeps protection disabled |
| `PROTECTION_MODEL_DIR` | `.local/models/segformer_b2_clothes` | Pinned locally provisioned parser; helper never downloads it |
| `MAX_IMAGE_BYTES` | `10485760` | Maximum encoded bytes per image |
| `MAX_IMAGE_PIXELS` | `16000000` | Maximum decoded pixel count; includes the evaluated high-resolution garment references |
| `QUEUE_CAPACITY` | `5` | Queued/processing jobs, including uncertain active submissions |
| `POLL_SECONDS` | `1` | History/queue polling interval |
| `DEADLINE_SECONDS` | `1800` | Waiting deadline after durable submission intent |
| `RETENTION_SECONDS` | `86400` | Retention after a verified terminal outcome |
| `CLEANUP_INTERVAL_SECONDS` | `60` | Periodic cleanup interval; also runs on startup |

The 1,800-second deadline includes submission/queue waiting after intent. Advanced
three-image research recorded a successful native execution of 967.796 seconds,
which exceeded the earlier 900-second default. This allowance does not promise
completion within thirty minutes or cancel upstream GPU work when waiting expires.
Numeric limits must be finite and positive. Keep the local application on loopback.
Hosted authentication, ownership, quotas and private topology are implemented
and controlled-tested; see DEPLOYMENT.md for the preparation-only boundary.

## API behavior

The five endpoints are defined in ROADMAP.md. `POST /api/try-on` accepts multipart
`person`, `garment`, `category` and optional nonnegative 63-bit `seed` (default 0).
Qualified reference mode also accepts optional `back`, `side`, `detail` photos;
layering accepts `outer` plus `outer_category`, with no optional view photos in
that request. The person is included in the five-image hard maximum. Unknown or
duplicate roles fail. A mode, category/combination or view absent from the current
qualification fails closed. Structured roles determine the graph's image order.
Supply an `Idempotency-Key` header, up to 128 characters, when submitting or
retrying a request. An identical key/request returns the original job; changed
inputs/category/seed return 409. A fresh generation uses a fresh key and seed.
Without a key, each accepted request creates a new job.

Only one image per role is allowed. Actual decoding determines supported format:
single-frame PNG, JPEG or WebP. File and pixel limits are enforced, and the entire
multipart body is bounded before parsing, even without Content-Length. EXIF
orientation is applied; alpha is composited on white; normalized RGB PNGs contain
no original metadata. Original/normalized hashes and geometry are recorded.
The browser cannot supply an arbitrary inference graph.

Optional `protect_regions=true` applies only to a qualified one-reference job.
It requires its separate passed 40-output study, exact CPU-engine parity, unchanged
implementation/parser files and an explicitly configured existing interpreter.
Unqualified protection fails with503; it does not silently opt the user in.
The CPU helper runs independently of the API event loop, with a90-second deadline
and cancellation that stops its owned process. Ambiguous hair/neck boundaries or
parser/runtime failure retain the validated raw preview with a recorded fallback.
The manifest records source/raw/final hashes, protected-pixel counts and wall time.
Owned helper artifacts follow the same job-folder deletion and retention policy.
This research model's separate rights remain in THIRD_PARTY_NOTICES.md.

`backend/workflow.json` versions graph/node mappings and candidate prompts. The
configured graph checksum must match. Category admission requires a fully passed
40-output report, all category thresholds, matching prompt hashes and the pinned
environment hash and exact workflow-template hash. Failed, absent or mismatched reports enable no categories.
Synthetic reports used in API tests are test fixtures, never evaluation evidence.

The health endpoint reports application health and ComfyUI HTTP connectivity
separately. A reachable service alone does not prove all required nodes/models are
ready. Readiness checks required graph node classes and configured model choices
against the native node catalog; malformed or missing information fails closed.

The worker waits for existing upstream queue work, then processes one application
job at a time. It saves the exact graph and submission intent before POST. Lost
acknowledgements are reconciled against client ID and exact graph in queue/history;
they are never blindly resubmitted. A retained unique PNG can recover completion
only after its embedded graph and upstream input hashes match. Missing GPU timing
remains null. An uncertain job without sufficient evidence remains tracked.

Statuses include stage, upstream activity, expiry and a generation manifest.
Native history timestamps supply GPU execution duration when available; retrieval
wall time is distinct. Model/environment hashes, sampler, prompts, uploaded image
hashes, graph hash, output hash and geometry remain attached to the job.

A deadline reports failure while tracking continues. It does not cancel GPU work.
A subsequently verified output can become complete; the manifest retains
`deadline_exceeded`. Deletion is rejected until upstream activity is resolved.
Completed/failed temporary assets expire after 24 hours by default. Cleanup checks
job prefix, resolved containment and bytes before removing upstream assets; it
preserves changed or unrelated files. Explicit deletion also removes the local job
folder and clears its manifest. The small durable status/idempotency row remains,
so stale requests cannot accidentally regenerate an expired job.

## Verification and remaining gate

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests -q -p no:cacheprovider --basetemp=.local/test-backend
```

The verified temporary test path is inside this checkout's ignored `.local` folder.
Ninety-one backend tests pass using a controlled external HTTP boundary and real
temporary SQLite/filesystem storage. They cover invalid uploads, bounded input,
normalization, idempotency/capacity, durable jobs, generation/result/manifest,
lost acknowledgements/restarts, native failures, malformed acknowledgements,
deadline tracking, owned deletion, retention and PNG recovery. HTTP smoke against
the actual local application verified connectivity, four quality-qualified
categories, the actual CPU adapter and offline/reconnected browser admission.
The three-live-generation gate now passes with exact native graph/submission,
source/result integrity, idempotent replay and restart/deletion evidence.

Checks also cover job/graph isolation, orphan cleanup, exact output/source integrity,
local Host/Origin controls, JWT signature/issuer/audience/expiry and owner isolation,
persisted quotas, optional reference mapping and bounded opt-in saved copies.
The coat-only refinement has a separate module binding and retains the full
eight-output denominator and original seven-pass floor; changed revisions,
missing reviews, extra combinations and lowered denominators fail admission.
Live acceptance supplements these controlled tests; it does not establish
hosted performance or quality of separately gated reference/outfit modes.

The conditional source-bag choice is part of request identity. The same request
key and choice return the existing job; a changed choice conflicts before a new
GPU submission. Historical requests without that option retain their fingerprints.
