# Hosted deployment preparation

On 2026-10-04 the owner additionally authorized free private web access using
the existing Windows GPU PC and Vercel. That separate setup is tracked in
[WEB_GPU_PC.md](WEB_GPU_PC.md); it does not provision a paid or Linux GPU host.
The container topology below remains prepared and unlaunched.

The owner authorized deployment files only and no paid services. Application and
worker images were built locally; no services, cloud machines, identity
registrations, GPU reservations or public endpoints were launched. The Compose
configuration has been parsed and its private network,
port, storage, privilege and quota settings checked by `deployment/validate.py`.
Both builds and dependency checks pass; hosted end-to-end behavior remains unverified.

## Prepared topology

TLS → OAuth2 Proxy → application → private ComfyUI worker. Only TLS publishes a
port, bound to `127.0.0.1:8443`. Worker and application publish no host ports.
The worker's network is internal and it has no outbound network. Models are
operator-provisioned read-only files; the image never downloads model weights.
The startup script checks all three model checksums, the custom node and Torch.
The evaluated ComfyUI commit and registry node archive are pinned. Image-only
worker dependencies use recorded local version constraints. The mismatched local
audio package is omitted because no audio node belongs to this workflow. Linux
GPU execution and a fresh Linux quality gate are required before claiming equivalence.
Compose deliberately points at separate `summary_hosted.json` and
`feature_quality_hosted.json` reports, which are absent until that qualification.
It does not enable hosted generation from the local Windows acceptance report.

OIDC is restricted to RS256 and one configured issuer/audience. The gateway
strips incoming authorization, validates sign-in, and forwards its signed ID token.
The backend verifies the signature again with bounded HTTPS JWKS retrieval and
requires issuer, audience, expiry, issued-at and subject. It stores a hash of the
issuer/subject pair, rather than tokens or email addresses. HTTP tests verify
job/photo/look isolation, independent idempotency keys, wrong and expired claims,
origin/host rejection, quotas and rate limits. Authentication cookie settings use
Secure, HttpOnly, SameSite=Lax, PKCE S256 and OIDC nonce validation.
Configuration follows the official [OAuth2 Proxy documentation](https://oauth2-proxy.github.io/oauth2-proxy/configuration/overview/).

## Limits and storage

One worker executes jobs serially. Five unfinished application jobs, ten new
generations per user per UTC day and twenty total new generations per UTC day
are permitted; replaying an identical request key does not consume another slot.
Accepted failed attempts still count. The daily limits persist across restart.
Verified users are limited to 120 API calls per minute. TLS adds a bounded IP
request rate. These limits cap inference requests; they do not cap a provider's
idle-machine bill. There is no autoscaler or cloud provisioning configuration.

Uploads are limited to 10 MiB and 16 million pixels each, normalized to PNG.
Temporary inputs, results and owned inference copies expire 24 hours after the
terminal job, with a cleanup sweep each minute. Work still active on the GPU is
tracked before deleting its files. Saved looks require explicit consent, persist
until deletion, and share a global maximum of twenty looks/256 MiB. Downloads
remain under the user's control. Both volumes are private to this deployment;
any later backups must implement the same photo deletion policy before use.

Application logging includes request ID, status and duration; access logs and
gateway authentication/request logs are disabled to keep paths, tokens, email and
photos out of logs. Container logs rotate at three 10 MiB files per service.
Application and worker health checks detect process availability; application
health separately reports workflow/model readiness and validated categories.
An external health monitor is not provisioned.

## Operator preparation, without launching

1. Keep `deployment/.env.example` as a template. Populate a private `.env` with
   the exact HTTPS public origin (no trailing slash), OIDC issuer, JWKS URL,
   registered client ID and permitted email domain. Register the exact callback
   `${PUBLIC_ORIGIN}/oauth2/callback` with the operator's identity provider.
2. Supply private `deployment/secrets/oidc_client_secret` and
   `deployment/secrets/session_cookie_key`. The first contains the client secret
   without a trailing newline. The second contains exactly 32 random binary bytes.
   Do not print either file or pass secret values on a command line.
3. Place operator-owned certificates in ignored `deployment/tls/fullchain.pem`
   and `privkey.pem`; grant only the TLS service identity read access.
4. Point `MODEL_DIRECTORY` at existing files in `diffusion_models/`,
   `text_encoders/` and `vae/`. No credentials or photos belong in the build context.
5. Run `.venv\Scripts\python.exe deployment\validate.py`. This only reads files
   and executes Compose's configuration parser; it creates no resources.

## Measurements and release dependencies

Both application and worker images were built locally with Docker Desktop's Linux
engine. The final application image runs all 91 controlled backend tests during build;
they pass on Linux as well as Windows. Both images pass `pip check`. Build context
excludes photos, models, databases and secrets. No application, GPU worker or
gateway container was started, and no image was pushed to a registry. Image build
success does not establish Linux GPU execution, model quality or hosted readiness.
Local preparation tags are `comfyfitter/app:prepared-local` and
`comfyfitter/worker:prepared-local`. The final application image includes the
qualified conditional shirt+coat report and compiled browser UI. Its image ID is
`sha256:d60a525143b4e250fedbdcbbfaef434d46de610d197649ab93eb8ef314526bcf`.

The selected local category_reference_v4 completed 40 outputs with median
generation 197.57 seconds and sampled peak device VRAM 7,388 MiB. These are Windows RTX 5060 observations,
not hosted cold-start, throughput, Linux quality or generation-cost measurements.
Hosted release requires a build on the intended Linux GPU runtime, three live
application generations, signed-in browser flow, worker restart/load/expiry tests,
external worker-port isolation checks, and provider billing measurements. Required
observations are startup-to-ready seconds, peak memory, accepted and rejected
load, recovery time, billable idle hours, and effective cost per completed preview.
No hosting target or price is asserted before those measurements.

The current Qwen weights permit research/evaluation under separate model terms.
The application's MIT license does not authorize unrestricted commercial model
deployment. See THIRD_PARTY_NOTICES.md. Hosted generation remains disabled until
its separate Linux quality report passes. Multiple-reference, constraint and outfit claims each
require their own declared evidence; deployment does not override these gates.
