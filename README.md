# Smart Align Nodes

Smart Align Nodes is a new Blender node editor add-on for inspecting, aligning, and later arranging selected nodes.

This repository starts from a fresh design. Earlier experiments from other repositories are not used as implementation context.

## v0.3.1

`v0.3.1` strengthens the debug-only build before alignment behavior is implemented.

It does not move nodes. Its purpose is to collect trustworthy node data before implementing alignment and smart tiling algorithms.

## Features

- Adds a `Smart Align` panel to the node editor sidebar.
- Adds `Debug Selected Nodes`.
- Writes selected-node diagnostics to a Blender text block named `Smart Align Debug`.
- Prints the same diagnostics to the system console.
- Reports Blender version, UI scale, pixel size, DPI, editor region size, and View2D scale.
- Preserves raw `location`, `location_absolute`, `width`, `height`, and `dimensions`.
- Reports the observed geometry ratio and a clearly labeled normalized box candidate.
- Reports Frame ancestry and the selected movement root for future two-phase layout.
- Treats Reroute locations as center anchors and reports a candidate collision box.
- Reports expanded socket state, socket links, and corrected node-level links.

## Installation

1. Download `Smart_Align_Nodes_v0.3.1.zip`.
2. Open Blender.
3. Go to `Edit > Preferences > Add-ons`.
4. Click `Install...`.
5. Select the zip file.
6. Enable `Smart Align Nodes`.

## Usage

1. Open a Blender node editor.
2. Select one or more nodes.
3. Open the node editor sidebar.
4. Open the `Smart Align` tab.
5. Click `Debug Selected Nodes`.

Open Blender's Text Editor and inspect `Smart Align Debug`.

## License

GPL-3.0-only.

See [LICENSE](LICENSE).
