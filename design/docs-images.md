# Documentation images

The source gallery is the **docs images** page in **Cortex DA 2**:
https://app.paper.design/file/01M25KM13W2VR3JT6KXR2Y7SHY/W-1

## Source and format

- 74 desktop application compositions, two reusable macOS templates and six
  full-background Higgsfield wallpapers.
- Composition canvas: 1680 x 1120. WebP exports: 3360 x 2240, at 2x.
- Application content comes from existing Paper designs, not generated UI.
- Existing macOS windows keep their native chrome. Other screens use the
  shared 44px title bar. Every image shows a complete application viewport.
- Light and dark pairings use actual matching source states. No missing dark
  variant is synthesized by recoloring a light screenshot.

These are **interface design previews**, not verified production captures.
Documentation frames say "Interface preview." Product behavior and limitations
in the article remain authoritative.

## Publication boundary

`docs-images.json` maps each composition to its source node, wallpaper and
Higgsfield generation. `galleryOnly` explains why an image must not be placed
in an article or copied into the public `images/product/` directory.

Excluded previews remain in Paper: unimplemented functionality, conflicting
limits or labels, unverified prices, mixed-language examples and the redacted
integration-key dialog. The source artboards are unchanged.

The selection covers full desktop feature views, including settings and
natural dialogs. It deliberately excludes mobile duplicates, component
specimens and redundant error states. No dedicated Cortex Design workspace,
CLI screen, SSH-host management screen or running Security scan was found in
the supplied sources. A Chat document canvas is not a Cortex Design screen.

## Updating an image

1. Update the composition in Paper, preserving the original source artboard.
2. Review framing, loaded image fills, chrome, language and visible claims.
3. Export the named composition as WebP at 2x.
4. Copy the approved export to `images/product/<name>.webp`.
5. Retain a meaningful alt description and explicit dimensions in MDX.
6. Put theme visibility classes on an enclosing `div`, not on the image,
   so the hidden variant's generated zoom control is hidden as well.
7. Run `node scripts/tests/docs-images.test.mjs` and the repository checks.

Do not automatically publish the entire gallery. An image excluded for a
content mismatch needs a fresh product check before its exclusion is removed.
