# Validation

## 2026-11-04: hairstyle integration (v0.2.0)

The following checks apply to the six-node merged package at this release,
using ComfyUI 0.43.0 and frontend 1.57.6. The test server enabled only
`comfyui-reference-gallery`; all six node definitions reported that package
as their owner. The main ComfyUI installation continued using the three
independent packages and was not switched to the merged package.

- The new six-node preview API workflow completed with six decoded preview
  images. The unchanged four-node preview API workflow also completed.
- The six-node UI workflow imported and exported all six reference connections
  through IMAGE output 0 without missing gallery nodes.
- Real Vue-renderer clicks opened the nested hairstyle UI, searched and selected
  a different hairstyle, and updated only that node. The random dice, selection
  lock and language switch worked without queueing a prompt. Selection,
  language and lock state survived workflow serialization and reload.
- The existing pose/costume browser smoke script passed: actual native-button
  clicks, selections, independent IDs, save/reopen and no automatic queue.
  Its representative random UI-message restoration check is separate from the
  actual six-node reference-image execution above.
- Python: pose 46 checks (44 passed, 2 optional library checks skipped),
  costume/package 15 checks (14 passed, 1 optional live-cache check skipped),
  hairstyle 36 checks (34 passed, 2 optional full-library translation checks
  skipped). Hairstyle translation checks then passed 3/3 with the installed
  library explicitly supplied. Windows tests used UTF-8 and a resolved long
  temporary-directory path.
- JavaScript: 48 checks, 44 passed and 4 optional browser/full-library checks
  skipped. New hairstyle script syntax checks passed. The real browser checks
  described above were run separately through Playwright CLI.
- Installer regressions: 25/25 passed, including the 14 existing pose/costume
  checks and 11 new hairstyle cases. Coverage includes pinned clone/ZIP,
  corrupt hashes, altered previews, missing files, duplicate IDs, path and user
  library containment, index-last publication and Windows CRLF text checkout.
- The unified CLI installed the complete hairstyle library offline from the
  pinned local source into an ignored test destination: 893 records, 2,679
  images and 2,011,434,211 image bytes. All three fixed Git image-tree hashes
  matched. A subsequent check of all 2,682 installed content SHA256 entries
  found no missing or changed files. This check verified file hashes,
  PNG chunk CRCs and PNG/WebP structure and dimensions, without full pixel
  decoding by the installer or assessing image-generation quality.

No Qwen or H3 model inference was run for this release. Full network archive
download was not repeated; the complete offline installation used the same
pinned source content. The original four-node release checks below are
historical results from 2026-11-03.

## 2026-11-03: original pose/costume integration

Validated on 2026-11-03 against ComfyUI 0.43.0 and frontend 1.57.6.
These results apply to the merged plugin, rather than only to the two original
packages. The live checks used an isolated ComfyUI instance with only this
custom-node package enabled.

## Compatibility and backend

- All four original node IDs were registered from `comfyui-reference-gallery`:
  `PoseGallery`, `RandomPoseGallery`, `CostumeGallery`, `RandomCostumeGallery`.
- Each node retained its original six outputs, input fields and identifier
  format. The original `/pose_gallery/*` and `/costume_gallery/*` routes worked.
- Pose user uploads and management records retain the original ComfyUI user
  directory and environment-variable overrides.
- Python suites: 46 pose tests (44 passed, 2 optional full-library checks
  skipped in the code-only checkout); 15 costume/package tests (14 passed,
  1 explicitly enabled live test initially skipped).
- The live cache test was then enabled and passed: a second WebSocket client
  received the random costume UI result after both nodes hit cache, with the
  same seed and the same preview image. Cached UI replay does not disable
  deterministic seeds or force model execution.
- The combined four-reference preview workflow completed successfully using
  the installed local libraries. No diffusion model was loaded for this check.

## Browser

- Tested both the traditional canvas renderer and Vue node renderer.
- Actual mouse clicks opened pose and costume galleries in both renderers.
  Canvas tests used widget geometry and real pointer clicks, not direct
  invocation of widget callbacks.
- Pose preview click, pose/costume selection, independent IDs, workflow
  serialization/reload, random UI restoration and random-pose language controls
  passed. Selecting a gallery item did not queue generation.
- Random preview restoration in the browser smoke script uses representative
  backend UI messages; actual node execution and actual cache replay were
  verified separately through the server.
- Both original plugins' preview workflows imported and exported API prompts
  without missing gallery nodes.
- Qwen Image 2.1 example import/export preserved reference 1 from Load Image and
  reference 2 from Costume Gallery, both using IMAGE output 0.
- JavaScript suites: 22 passed; 3 checks requiring optional fixture/browser or
  full-library conditions were explicitly skipped. Web scripts and embedded
  pose HTML scripts passed syntax/structure checks.

## Optional library installation

- Fourteen installer tests passed, including path/symlink containment, ZIP
  allowlists, duplicate entries, fixed revisions, user-library protection,
  invalid image formats and preserving the previous index on publication error.
- The unified CLI installed both complete libraries from the existing pinned
  sources into a temporary destination:
  - Pose: 1,439 records, 2,878 images, 691,586,721 image bytes.
  - Costume: 2,727 records, 5,454 images, 188,685,602 image bytes.
- All installed image references matched the actual file sets. PNG chunk CRC,
  JPEG/WebP structure and dimensions passed. This merge did not repeat complete
  pixel decoding or assess the visual quality of every image.
- Fixed upstream metadata URLs responded successfully. The merge validation
  used offline sources and did not repeat the complete network archive download.
- Images and original library metadata are excluded from this Git repository.

## Model-generation boundary

This merge was checked with real reference-image execution and Qwen workflow
wiring. It did not repeat Qwen model inference, assess every costume or pose,
or claim product-detail fidelity. Model weights and personal input images are
not included. Users must choose their own input image and local model paths.

## Running checks

Use a ComfyUI Python environment for the backend suites:

```bash
python -m unittest discover -s pose/tests -p 'test_*.py' -q
python -m unittest discover -s costume/tests -p 'test_*.py' -q
python -m unittest discover -s hairstyle/tests -p 'test_*.py' -q
python -m unittest discover -s tests -p 'test_*installer*.py' -q
node --test pose/tests/test_preview.mjs
```

The live cache test requires `COSTUME_CACHE_TEST_URL` pointing to a separate
test server. It queues only a random reference node and Preview Image.
`tests/browser_merged.js` is a Playwright run-code function; pass a UI workflow
object as `options.qwenWorkflow` to enable the Qwen wiring check. Screenshot
directories must be created by the caller.
