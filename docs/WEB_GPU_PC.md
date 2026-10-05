# Free web access through the existing GPU PC

The owner authorized Vercel web setup using the existing GPU PC on 2026-10-04.
No paid hosting is authorized. The website is a stable Vercel entry point; the
actual fitting room, durable jobs and photos stay on the evaluated Windows PC.
This retains the existing Windows quality gates rather than claiming a Linux
worker qualification. This connection is for the single owner's personal
research/evaluation under the separate model terms in THIRD_PARTY_NOTICES.md.

## Connection

Vercel serves `web/`, which opens an email-protected Cloudflare Quick Tunnel.
Cloudflared 2026.9.3 checks a one-time PIN and exactly one owner email before
forwarding a request. No Cloudflare account or domain is needed. The signed
official release digest is checked before launch. References:
[protected tunnels](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/)
and [connector authentication design](https://blog.cloudflare.com/protected-quick-tunnels/).

The connector reaches only the loopback gateway on port 8001. A fresh 256-bit
private connector host is required, the public HTTPS origin must match, and
cross-origin mutations fail closed. The gateway only forwards the existing
application's UI and explicit job/look routes to 127.0.0.1:8000. Native ComfyUI
8188, arbitrary local files and other applications are unavailable. Cookies,
identity credentials and forwarding headers are stripped before the local hop.
The gateway caps requests at 120/minute, new generation attempts at ten per UTC
day (durable across restart with idempotent retries), uploads at 50 MiB plus
multipart overhead and responses at 40 MiB. Existing application validation,
five-job queue, photo retention and saved-look limits still apply.

Exactly one owner may be invited, because this mode shares that owner's existing
local jobs and saved library. This is not a public multi-user production service.
Photos traverse Cloudflare's encrypted connection; they are stored by the
application on the PC. No photos or model files enter the Vercel deployment.

## Start and stop

With the local app and GPU worker ready, use
`scripts/Start-ComfyFitterWeb.ps1 -OwnerEmail '<your approved email>'`.
The verified connector is expected at ignored `.local/tools/cloudflared.exe`;
its official source is the 2026.9.3 Cloudflare GitHub release. The launcher
requires the protected startup message, exactly one address and a registered
connection before enabling the gateway. It starts hidden processes and records
their identities without installing a Windows service or changing firewall rules.

Set Vercel's non-secret `COMFYFITTER_PRIVATE_URL` environment variable to the
printed HTTPS tunnel origin, then redeploy the `web/` project. Never put an email,
token, private connector host, photo or model in that variable. Open the Vercel
website, follow its fitting-room link and complete Cloudflare's email PIN sign-in.

Use `scripts/Stop-ComfyFitterWeb.ps1` to stop only the verified launcher-owned
connector and gateway. It preserves the local app and GPU worker. The PC must
remain on and connected. Quick Tunnel URLs change after a restart; update the
Vercel variable and redeploy when that happens. Quick Tunnels have no uptime
guarantee and are intended for development. A stable tunnel hostname would
require a separate Cloudflare account/domain setup; it is not claimed here.

## Acceptance evidence

The gateway has fourteen controlled HTTP-boundary checks: connector/origin
admission, deny-native/arbitrary paths, credential stripping, mutation checks,
request limiting, failed-upstream behavior and persistent idempotent daily limits.
The Vercel destination has separate Node checks for safe HTTPS origin handling
and an explicit pending state. These do not establish successful tunnel login or
remote GPU generation. Live URL, email admission and real web generation must be
verified after the owner supplies the approved email and signs in.
