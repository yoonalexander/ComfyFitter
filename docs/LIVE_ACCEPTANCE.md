# Local application acceptance

Verified 2026-10-03 on the existing Windows RTX 5060/ComfyUI runtime.
The real application used the complete passing `category_reference_v4` report,
exact graph and category-specific prompts. These checks used licensed evaluation
photos and native GPU execution; no synthetic quality report enabled this app.

Three consecutive application generations completed successfully:

| Entry path | Category | Seed | Native execution seconds | Native submissions |
|---|---|---|---|---|
| Browser upload and generation | Hoodie | 3759931431 | 200.867 | 1 |
| Browser new-seed retry | Hoodie | 3346793533 | 206.614 | 1 |
| API restart/retrieval/deletion check | Jacket | 2026093001 | 203.287 | 1 |

Separate evaluation jobs shared the serial GPU between these application jobs.
Execution timings come from native history and exclude application queue waiting,
result retrieval and optional CPU protection. The browser jobs used the same
normalized input hashes and distinct seeds. Native history and immutable graphs
were checked, with one submission per application job. Replaying the API request
key returned its existing job rather than generating again.

The API check stopped and restarted only the owned application while its exact
job was running in ComfyUI's native queue. ComfyUI continued independently; the
restarted worker reconciled and retrieved its result. Result and source downloads
matched recorded hashes. API deletion removed owned application and inference
files; deleted result/input routes returned 410. An opt-in saved copy survived
another app restart with matching bytes, then its result, inputs and directory
were deleted and returned 404.

The real browser verified uploads, active refresh with restored photos/protection
choice, keyboard comparison (50 to 51), actual PNG download/hash verification,
new-seed retry and the raw-fallback notice. Its optional protection executed the
actual CPU helper. Explicit saved-look consent copied both references and the
result; all three survived app restart with matching hashes. Deletion through the
actual API removed those copies and the first temporary preview's native photos.
The browser displayed the deleted preview and an empty library after refresh.
The second temporary preview remains available until its normal 24-hour expiry;
downloaded files remain under the user's control.

With valid photos loaded, an offline application-to-image-service connection
disabled generation and displayed the service error. Restoring the connection
re-enabled generation automatically. This test changed only the app's connection;
it did not interrupt the GPU studies. Narrow layout, comparison, saved consent
and photo rendering were exercised in the real browser, alongside the earlier
controlled desktop/mobile checks.

The fixed-seed live jacket output was visually reviewed against its source,
reference and qualified benchmark. All five quality scores remain 2. Its inputs
have identical decoded RGB pixels after normalization, but the generated output
has small numerical pixel differences (mean RGB delta 0.353/255); generation is
not claimed to be pixel-identical across runs. CPU protection parity is a
separate deterministic comparison against the same retained raw inputs.

Retained private verification records: `.local/live-browser-verification.json`,
`.local/live-api-gate/record.json`, `.local/protection-adapter-verification.json`
and screenshots under `.local/screenshots/`. Evaluation retention is separate
from ordinary application upload retention. Photo files and records remain ignored.
This completes the local backend/browser acceptance gate, not hosted release or
the separate reference/outfit quality gates.

## Qualified hoodie detail references

After the fresh eight-output matched reference gate passed, an actual browser
job used person, hoodie front and licensed detail crop in that exact order.
Seed 1607723699 completed in 278.809 native execution seconds. Active refresh
restored all three inputs and the selected mode. Native history contained one
submission, with an exact immutable graph match; all retrieved input/result
hashes and the downloaded PNG hash were verified. Only hoodie/detail was offered.
The additional detail slot passed 1280-pixel desktop and 360-pixel narrow layout
checks with no horizontal overflow or missing images; the viewport override was
restored. Evidence is `.local/live-reference-verification.json` and
`.local/screenshots/live-reference-desktop.png`. This is a fourth actual app
generation, separate from the original three-generation MVP gate.


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
