# Algorithm Plan

This project starts from a clean design. The first implementation step is a debug build that measures Blender node data before any alignment algorithm moves nodes.

## Principles

- Do not reuse earlier add-on layout code or earlier node-size assumptions.
- Treat Blender-reported geometry as data to verify, not as truth.
- Keep `v0.3.0` read-only. It must not move, create, delete, or relink nodes.
- Use debug output to decide which geometry values are reliable.

## Data To Collect

For each selected node:

- `name`
- `label`
- `bl_idname`
- `type`
- `parent`
- `location`
- `location_absolute`
- `width`
- `height`
- `dimensions`
- raw boxes derived from width/height and dimensions
- input sockets
- output sockets
- socket links
- node-level links
- whether it appears to be a Frame
- whether it appears to be a Reroute

## Frame Rules

Future layout will process Frame selections in two phases.

1. If selected child nodes inside a selected Frame must move, move those child nodes first.
2. Refresh node geometry.
3. Re-read the Frame size after Blender updates it.
4. Use the updated Frame box when aligning the Frame with outside nodes.

Frame children should not be moved independently just because their Frame is selected.

## Isolated Nodes

Future smart tiling will separate selected connected components.

- Main connected data-flow components are laid out first.
- Selected nodes that are not connected to the selected data-flow tree are placed below the main layout.
- The vertical gap for isolated groups should be larger than normal node spacing.

## Line Avoidance

Future smart tiling should consider socket-to-socket line areas.

For a link:

- Estimate or read the output socket position.
- Estimate or read the input socket position.
- Treat the segment between them as a line to avoid.
- Prefer layouts where unrelated node rectangles do not overlap that segment.

This requires reliable node boxes and socket positions, so it must be implemented after debug data has been reviewed.

## Directional Alignment

Future directional alignment will only consider selected nodes as blockers.

- Left or right movement checks vertical range overlap.
- Up or down movement checks horizontal range overlap.
- If selected nodes already overlap before alignment, separate them first.

Unselected nodes should not block directional alignment.
