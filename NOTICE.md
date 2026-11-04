# Sources and library scope

This repository distributes plugin code, tests and installers. Gallery image
files and original catalog metadata are obtained separately only when the user
explicitly runs an installer. The running plugin uses local files.

## Pose

The pose gallery UI is adapted from wangweihong/ai-pose-gallery-zh, a fork of
Anhao's Chinese gallery. The fixed optional library revision is
`072a3690af6e7e0011abbe0fa1ccc08939fbb47d`:
https://github.com/wangweihong/ai-pose-gallery-zh/tree/072a3690af6e7e0011abbe0fa1ccc08939fbb47d

Chinese adaptation: Anhao, https://github.com/anhao/ai-pose-gallery-zh.
Original pose artwork: ギア (@giaaibusi), https://x.com/giaaibusi and
https://ai-pose-gallery.pages.dev/.

The complete upstream LICENSE, including its scope paragraph, is preserved
in `sources/pose/LICENSE.upstream.txt`. It credits Copyright (c) 2026 Anhao
and applies MIT to code only. It explicitly excludes images, thumbnails and
original metadata from MIT and states that those materials must not be used
commercially. Installing an optional library does not change these terms.

## Costume

Source: https://github.com/paipiange/nvzhuang/tree/b236f0118e3a0195d1c71a7945f45294199f9607.
The complete MIT LICENSE, Copyright (c) 2026 paipiange, is preserved in
`sources/costume/LICENSE.upstream.txt`.

The upstream README credits @giaaibusi as original author / inspiration. Its
anime import script identifies https://ai-costume-anime-gallery.pages.dev/
as the anime metadata and image source. The optional installer obtains 1407
real-style and 1320 anime-style records, with display WebP and thumbnail WebP
files. These WebPs are not the original PNG files; original PNGs are excluded.

At the fixed revision, the README and release audit describe the code and
gallery assets as MIT, including commercial use and redistribution. However,
section 3 of `docs/LICENSE-DECISION.md` says image/data assets must not be
packaged, redistributed or directly sold, and must not be called MIT or CC0;
earlier sections of that same file say the code and 1407 images are MIT.
This is an unresolved inconsistency in the upstream documents, not a new
license grant or an independent confirmation of third-party asset rights.

Fixed source documents:
- https://github.com/paipiange/nvzhuang/blob/b236f0118e3a0195d1c71a7945f45294199f9607/README.md
- https://github.com/paipiange/nvzhuang/blob/b236f0118e3a0195d1c71a7945f45294199f9607/docs/LICENSE-DECISION.md
- https://github.com/paipiange/nvzhuang/blob/b236f0118e3a0195d1c71a7945f45294199f9607/docs/LINUXDO_RELEASE_AUDIT.md

Neither upstream's external AI generation/try-on service, analytics nor Go
backend is included or executed by the library installers.

## Hairstyle

Code and UI source: https://github.com/wangweihong/comfyui-hairstyle-gallery/tree/f72dc1881f92a40e52bd0fbf53d33c24d35c4c5b.
This integration includes the native-button fixes for the ComfyUI Vue node
renderer and keeps the original node IDs, HTTP routes and user library paths.

The optional library is pinned to that revision: 893 PNG originals, 893 WebP
previews and 893 WebP thumbnails. It is installed explicitly, not distributed
in this repository. Original gallery indexes and generation records are also
excluded. The small English-name dictionary needed by the runtime is retained
with its upstream provenance; the independent-code MIT grant does not extend
to original or translated metadata.

The full upstream license and third-party statement are preserved in
`sources/hairstyle/`. Upstream credits あぎ (@agi_aibusi) and
https://ai-portrait-gallery.pages.dev/ as the original portrait source, and
describes the hairstyle library as generated mannequin references derived from
893 front-facing portraits. The statement records the source site's CC0 label
and its request to avoid direct redistribution of the image dataset. Models
and LoRAs are not included, and their terms are not changed by this plugin.
