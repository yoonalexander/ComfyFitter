# Local browser application

## Setup and launch

Prerequisites: Python 3.13, Node 24, the separately installed ComfyUI/runtime and
model files described in SETUP.md. The application environment remains separate
from the GPU environment. From this checkout:

```powershell
.\scripts\Setup-ComfyFitter.ps1
.\Start-ComfyFitter.cmd
```

The launcher builds no models and changes no ComfyUI installation. It starts a
single application process on `127.0.0.1:8000`, serves the built UI and opens the
browser. It reports image-service readiness and whether quality validation enables
any categories. Use `scripts\Start-ComfyFitter.ps1 -NoBrowser` for an API-only
launch, or `-Port 8001` if port 8000 belongs to another application.

```powershell
.\scripts\Stop-ComfyFitter.ps1
```

Shutdown checks that the recorded PID belongs to this application's Python and
Uvicorn command. It stops the app without interrupting ComfyUI. Submitted GPU work
can continue and is reconciled when the application restarts. Startup/shutdown
were exercised locally; logs and process metadata are under ignored `.local`.

## Behavior

Choose one person photo and one clear garment reference. Actual PNG/JPEG/WebP
decoding, size and pixel limits are checked in both browser and API. Remove or
replace either photo; category choices reflect the validated workflow. Service
readiness, queue/generation/reconnection/error stages and expiry are shown.

Submission keys prevent duplicate inference after a lost acknowledgement. A page
refresh restores job status and its normalized input photos from private server
storage. Browser storage contains job IDs and request fingerprints, not photos.
Before/after comparison supports a keyboard slider. Download returns the actual
PNG. Trying another seed reuses inputs and submits one fresh seed/request key.
Temporary images expire after 24 hours or explicit deletion. Saved looks copy
the person, all supplied garment references and result only after explicit consent and persist until deletion, independently
of temporary job expiry. The library enforces count and byte limits.

When a mode passes its separate quality gate, reference options expose ordered
back, side and detail slots for the same front reference, or an explicit inner
garment plus outer jacket/coat. Categories, reference roles and combinations
remain limited to the published qualification. One-reference mode remains
available. Refresh restores every accepted reference from private job storage;
unconfirmed submissions retain their original ordered file fingerprints.

After its separate study and CPU-runtime checks pass, one-reference mode can offer
optional source protection. Its opt-in choice survives submission recovery and
refresh. Uncertain boundaries retain the standard preview and show that fallback.
The shipped hosted configuration leaves this CPU helper disabled; local setup must
explicitly identify the existing pinned parser interpreter and provisioned model.
Use `scripts\Start-ComfyFitter.ps1 -ProtectionPython C:\path\to\existing\python.exe`
after qualification. The launcher remembers that local path in ignored
`.local/application-runtime.json`; it installs or upgrades nothing. Exact runtime
package checks keep protection disabled when the configured environment drifts.

## Verification boundary

Controlled browser checks on `127.0.0.1:8801` verified upload, refresh during active
work without duplicate submission, keyboard comparison, download bytes, one-click
new-seed retry, service-offline recovery, explicit saved-look consent, and narrow
360-pixel layout without horizontal overflow. Synthetic acceptance data is confined
to `scripts/browser_fixture.py`; this process never contacts the GPU. The real
application now offers four categories from the complete passing v4 report and
optional guarded source protection. The real browser on `127.0.0.1:8000` also
verified disabled generation with valid photos while its service connection was
offline, then automatic recovery when connectivity returned. Two actual browser
GPU jobs verified upload, active refresh, source/protection restoration, keyboard
comparison, downloaded PNG hashes and new-seed retry. Saved copies survived app
restart and were fully deleted through the real API; the browser showed the
deleted-preview state and empty refreshed library. A third actual API job
verified restart during native execution without resubmission. See
[live acceptance](LIVE_ACCEPTANCE.md) for measurements and retained evidence.
The retained actual preview also passed a 1280 by 900 desktop breakpoint check:
all images loaded, and the document width stayed within the viewport. The normal
browser size was restored afterward; private evidence is
`.local/screenshots/live-desktop.png`.

The qualified hoodie front/detail mode also completed a real three-input browser
generation in 278.809 seconds. Refresh during execution restored the person,
front and detail inputs. Native history confirmed one submission and the exact
job graph; retrieved input/result hashes and the browser download matched the
manifest. Its 1280-pixel desktop and 360-pixel narrow layouts had no horizontal
overflow or missing images, and the temporary viewport override was reset.
This additional live seed is separate from the declared eight-output quality
matrix. Private proof is `.local/live-reference-verification.json` and
`.local/screenshots/live-reference-desktop.png`.


The conditional outfit candidate has a separate source-photo choice, "My photo
includes a bag or backpack." Its controlled browser fixture verified both
boolean choices against distinct API submissions, restored three references and
the checked choice after active refresh, and reset the choice when replacing the
person photo. Desktop 1280 and narrow 360 layouts had no overflow or missing
images; the viewport override was reset. This fixture uses synthetic images and
cannot establish native model quality or enable the real application. The
real outfit option requires the complete independently published quality gate.


## Qualified conditional shirt+coat browser acceptance

After all eight fresh V5 results were reviewed and the unchanged 7/8 floor
passed, the actual application offered only shirt+coat. Browser job
`fe25f94b-2098-489d-b72e-dec07db39e29`, seed 2248153020, completed in
283.58 native GPU execution seconds. It used the licensed person, blue denim
shirt and tan coat references, with the source bag choice checked. Refresh
during execution restored all three photos and that choice. Native history
confirmed exactly one submission and the exact immutable job graph; each
normalized input and the retrieved result matched its manifest hash. The
browser-downloaded PNG matched result SHA-256
`b4deea77cd6733fd8e0a03191fd526df291e01aea308c986a3998aa3081db7f5`.

The actual result preserved the face, pose, lower clothing, studio background,
existing backpack and straps while showing both layered garments. Minor trim
details remain approximate. This random-seed acceptance output is separate
from the declared eight-output quality matrix and does not change its 7/8 score
or the retained field-case inner-shirt neckline failure. Shirt+jacket remains
unqualified.

Desktop 1280 by 900 and narrow 360 by 800 checks found no horizontal overflow
or missing images; document widths were 1265 and 345 respectively. Keyboard
comparison reached 100, showing the whole generated preview. The temporary
viewport override was reset. Private evidence is
`.local/live-outfit-verification.json`, `.local/live-outfit-native-history.json`,
`.local/live-outfit-desktop.png` and `.local/live-outfit-narrow.png`.
This is the fifth successful actual application generation, separate from the
original three-generation MVP gate. The local app remains available at
`http://127.0.0.1:8000/`; temporary uploaded assets expire after 24 hours and
the downloaded PNG remains under the user's control.
