# Implementation and verification ledger

Updated 2026-10-04. Scope: finish Phases 0-7, with hosted work limited by the
owner to deployment-file preparation and no paid services. MIT applies to the
application. Acceptance criteria remain in [ROADMAP.md](ROADMAP.md).
The local roadmap and deployment-file preparation are complete for the offered feature scope.
Implementation and a passed live quality gate are separate; unqualified
combinations remain unavailable. Live hosted release is excluded by the owner.

The owner subsequently prioritized the local desktop application on 2026-10-04.
The experimental web tunnel is stopped and further web work is deferred.
See [desktop setup](DESKTOP.md) for the native window and local startup/recovery.

The owner's earlier request on 2026-10-04 authorized free private web access
through Vercel and the existing GPU PC. That additional work is tracked in
[WEB_GPU_PC.md](WEB_GPU_PC.md), with 14 new gateway checks (91 backend checks
total) and two web-entry checks passing. Vercel is deployed and connected to the
running tunnel; one-email admission and anonymous rejection are verified. The
owner's initial PIN opened the fitting room, but session persistence and actual
remote generation remain pending; paid hosting is excluded.

| Phase | Current evidence | Required remaining evidence |
|---|---|---|
| 0: baseline | Editable/API graphs, verified environment/model hashes, setup, recolor reproduction, MIT and third-party notices | Complete; research-model rights remain separate |
| 1: single garment | Fresh category_reference_v4 passed 36/40, with 9/10 in every category. All 40 runs reviewed and graph/source/output evidence validated. Median execution 197.57 seconds, sampled device peak 7,388 MiB. Exact graph and three prompt hashes bind application admission. Earlier rejected benchmarks remain published | Complete; small engineering dataset and single AI reviewer do not establish population accuracy or physical fit |
| 2: backend | 91 controlled backend tests plus three consecutive successful real application generations. Native history/graph and source/result hashes checked; idempotent replay, restart during native execution, owned deletion and saved-copy restart verified | Complete; see LIVE_ACCEPTANCE.md. Hosted runtime remains separate |
| 3: browser | Actual browser upload, GPU generation, active refresh, restored protection choice, keyboard comparison, PNG download/hash, new-seed retry, offline/reconnection, opt-in saved copies, restart and deleted-preview UI verified. Build and controlled desktop/narrow checks pass | Complete; the retained actual retry preview expires after 24 hours |
| 4: references | Fresh eight-output hoodie-detail study passed matched preservation with a modest aggregate +1 detail score. Both five-input capacity runs completed; median 443.62 seconds, peak 7,694 MiB. Actual three-input browser preview completed in 278.809 seconds; refresh/input restoration, native one-submission graph, retrieved/downloaded hashes and responsive layout verified. App offers hoodie front/detail only | Complete; no jacket/back/side quality claim. Capacity outputs executed successfully but failed try-on quality. Original rejected views retained |
| 5: constraints | Guarded refinement passed all matched non-regression checks, retaining 36/40 quality passes. Protection applied to 9 outputs and fell back to raw for 31. Accepted protected-region changed pixels fell from 5,997,294 to zero. All 40 actual engine outputs/masks and four real CLI calls match; actual async application adapter also matches. Optional protection enabled locally with the existing pinned CPU runtime | Complete; conservative unguarded refinement rejected at 35/40. Protection often falls back and does not repair raw garment defects; hosted CPU helper remains disabled |
| 6: outfits and saved looks | Original full sixteen-output study rejected: shirt+jacket 2/8, shirt+coat 6/8. Full sixteen-output v2 also rejected: 5/8 each. Fresh coat-only v3 rejected at 5/8; lower clothing improved but both studio backpacks disappeared and one shirt closure failed. All eight reviewed, including exact late native success recovered without resubmission; missing VRAM/wall measurements flagged. V4 rejected at 2/8: bag wording invented props on bag-free photos; one stalled owned worker case remains a failure with its exact ownership/exit audit. All seven actual outputs reviewed. V5 retained all original eight coat subjects/seeds and passed the unchanged 7/8 floor with an explicit source bag choice. All eight actual outputs reviewed and fully validated; final field seed retains an inner-shirt neckline failure. Median 282.15 seconds, device peak 7,680 MiB. Only shirt+coat enabled. Real opt-in copies survived restart and were fully deleted | Complete: actual browser preview finished in 283.58 seconds; active refresh restored three photos and the bag choice. One exact native graph, all input/result/download hashes and 1280/360 layouts verified. All earlier rejections retained; one matrix neckline failure and jacket combinations remain unqualified |
| 7: hosted preparation | JWT issuer/audience/expiry/signature, owner isolation, persisted quotas, request limits, private storage and queue controlled-tested. Private GPU/app, OIDC/TLS gateway and pinned files prepared; read-only Compose validation passes. Updated app and worker images built locally; 91 backend tests pass in the final Linux app image, its compiled frontend build passes and both images pass dependency checks | Complete for deployment-file preparation. Hosted GPU, authentication and performance remain unverified; live hosting is excluded by deployment-files-only instruction; no cloud resources provisioned |

## Decisions and evidence boundaries

The fresh baseline is a complete rerun, not selected outputs combined from older
experiments. Prompts, graph, cases and seeds were declared before submission in
`evaluation/category_reference_v4_protocol.json`. Feature studies have separate
locked protocols and do not inherit single-garment quality claims.

The one-reference application now uses the complete passing v4 report. Synthetic
acceptance reports exist only in controlled API/browser fixtures. Those checks
do not substitute for live generation or model-quality review. GPU studies run
serially on dedicated local ComfyUI. Licensed inputs/results remain ignored.
VRAM samples include desktop activity.

The original recovered jacket output has a verified embedded graph but lacks its
old execution history, timing and VRAM; no measurements were invented. Fresh
feature outputs retain native history, exact graphs and input/output hashes.

Earlier spatial studies expose parser ambiguity that restored old clothing and
damaged coat silhouettes. All rejected studies remain published. The accepted
guarded study uses a predeclared uniform fallback, rather than selecting cases or
seeds. The actual CPU helper restores source pixels only after native generation;
it does not establish a new native masked sampling graph.

## Resume

Consult ignored `.local/continuation.json` for process/session IDs. Inspect saved
submission records and native history/queue before restarting any GPU script.
Nonterminal feature submissions are deliberately not resubmitted. Preserve
intentional local work, model files and evaluation evidence. Never use test-only
reports to enable the real app.

The owner selected MIT and no paid services. The later 2026-10-04 request
additionally authorizes free Vercel access using the existing Windows GPU PC;
paid GPU hosting remains excluded. Model rights are separate in
THIRD_PARTY_NOTICES.md.
See [BACKEND.md](BACKEND.md), [BROWSER.md](BROWSER.md) and
[DEPLOYMENT.md](DEPLOYMENT.md) for implementation details.
