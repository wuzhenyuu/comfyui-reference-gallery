# Validation

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
python -m unittest discover -s tests -p 'test_installers.py' -q
node --test pose/tests/test_preview.mjs
```

The live cache test requires `COSTUME_CACHE_TEST_URL` pointing to a separate
test server. It queues only a random reference node and Preview Image.
`tests/browser_merged.js` is a Playwright run-code function; pass a UI workflow
object as `options.qwenWorkflow` to enable the Qwen wiring check. Screenshot
directories must be created by the caller.
