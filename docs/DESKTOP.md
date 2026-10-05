# ComfyFitter for Windows

The owner switched the active priority to a local desktop app on 2026-10-04.
The web tunnel is stopped. The Vercel experiment did not pass session-persistence
or remote-generation acceptance and is deferred.

## Open the application

Use the **ComfyFitter** shortcut on the Windows desktop. The app opens in its own
WebView2 window, starts the local application and isolated GPU service when they
are absent, and reuses them when they are already running. No browser login,
tunnel, hosting account or internet connection is needed for generation after
the existing runtime and models have been installed.

The first cold launch can take a few minutes. Startup shows the current stage;
a failure shows a specific reason and **Retry startup**. Once in the fitting
room, **Reconnect local services** can restore a stopped service. An unrelated
process on either port is preserved and reported rather than terminated.
Retries never submit a generation or start a second instance of a still-running
service. Generation quality, supported garment modes and model hashes remain
the same as the qualified local application.

Upload a person photo and garment reference, select a supported category, then
generate, compare and download. Hoodie front/detail and shirt+coat are the
qualified optional reference modes. Native file selection and downloads use
the Windows WebView2 controls. Photos remain in the existing local app storage;
saved looks require consent. Temporary photos expire after 24 hours as before.

Closing the window leaves the local services and any running GPU job alive.
Reopen the shortcut to resume the selected job; desktop browser state uses a
persistent, project-specific profile. This behavior prevents window closure
from interrupting generation. It also means the GPU service may keep models in
memory after the window closes. The existing local server stop procedure is
separate; wait for jobs to finish before shutting down the GPU service.

## Setup on this workstation

```powershell
scripts\Setup-ComfyFitterDesktop.ps1
scripts\Start-ComfyFitterDesktop.ps1
```

For a different existing ComfyUI installation, pass `-ComfyRoot '<folder>'` to
the setup script. The directory must contain `main.py` and
`.venv\Scripts\python.exe`. The default finds the existing Comfy Desktop runtime
under `%LOCALAPPDATA%`. The launcher binds both services to 127.0.0.1, reuses
the captured models/custom nodes, and configures the existing source-protection
Python. It does not install or download models, register a Windows service,
alter the firewall or create paid resources.

This is a desktop installation for the current checkout and existing GPU PC,
not a standalone distributable installer. Python dependencies are pinned in
`desktop/requirements.txt`; setup also installs the existing backend lock and
builds the React UI. WebView2 Runtime and .NET are prerequisites, as documented
by [pywebview](https://pywebview.flowrl.com/guide/installation.html). Native
window dependencies are separate from the model Python environment.

## Diagnostics and verification

Startup/service logs are under ignored `.local/logs/desktop-*.log`.
`.local/desktop/native-ready.json` is written by the actual React UI through
the native bridge after the local health check succeeds. This establishes
native WebView2 loading and service readiness, not visual output quality.
Window/profile/configuration state is private under `.local/desktop/`.

Controlled runtime tests cover reuse, foreign-port preservation, concurrent
retry, nonduplicating startup, visible errors/retry and rejecting hosted mode.
Frontend API tests cover unexpected authentication pages, actionable connection
errors, retained image-validation instructions and normal JSON parsing.
The existing GPU quality and actual-generation evidence remains documented in
the evaluation and local acceptance reports; it is not redefined as desktop
file-dialog acceptance.

Current workstation verification: native WebView2 loaded the actual React UI and
reported GPU readiness through the desktop bridge. After confirming the owned
queue was idle, both services were stopped and the desktop controller restored
them in 24.45 seconds. The 91 existing backend checks plus seven desktop runtime
checks pass, all four frontend API checks pass, and the production frontend build
and Python dependency check pass. Native file selection/download dialogs still
need a hands-on acceptance check; their availability is configured, not claimed
as visually verified by the native readiness marker.
