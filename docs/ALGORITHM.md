# Algorithm Plan

This project starts from a clean design. The `v0.3.x` debug builds measured Blender node data before any alignment algorithm moved nodes. Interactive snapping begins in `v0.4.0`; later releases refine collapsed-node, Reroute, Frame, and placement behavior.

## Principles

- Do not reuse earlier add-on layout code or earlier node-size assumptions.
- Treat Blender-reported geometry as data to verify, not as truth.
- Keep the debug operator read-only. It must not move, create, delete, or relink nodes.
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
- Blender version and display scaling values
- observed `dimensions.x / width` ratio
- normalized box candidate with its calculation basis
- Frame ancestry and selected movement root
- Reroute center anchor and candidate collision box
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

## Interactive Snapping

Direction-key alignment is no longer planned. Interactive movement will use guides similar to presentation and design applications.

- Normal nodes can snap by left, right, top, and bottom boundary guides.
- Reroute nodes use their center as the primary anchor.
- A vertically moving Reroute can snap its center to estimated socket heights on normal nodes so a link can approach a horizontal segment.
- Reroute chains should prefer equal center `y` values for horizontal routing and equal center `x` values for vertical routing.
- Socket positions require a separate derivation strategy because Blender does not expose their draw coordinates through the public Python API.

Snapping must work without enabling Blender's grid quantization.

### Geometry Anchors

Normal nodes and Frames expose four matching anchors:

- left and right
- top and bottom

Reroute nodes expose horizontal and vertical center anchors. Normal nodes also expose estimated socket-height candidates for vertical Reroute snapping. A multi-node selection uses the outer box of its movement roots and preserves its internal layout.

Blender's public Python API does not expose final socket draw coordinates. Socket heights are therefore estimated from the rendered node box, socket order, visibility, and collapsed state. This estimate is isolated from boundary geometry so it can be refined without changing ordinary node snapping.

### Equal Spacing

Spacing is measured between node boundaries, not between node centers.

For horizontal nodes `A`, `B`, and moving node `M`:

```text
gap(A, B) = B.left - A.right
gap(B, M) = M.left - B.right
```

Sequence extension snaps when these gaps are equal. Insertion between two neighbors solves:

```text
M.left - A.right = B.left - M.right
```

The same calculation is applied vertically with top and bottom boundaries. A spacing candidate is valid only when all three boxes have a real overlap on the orthogonal axis. Its measurement guides are drawn through that common overlap region.

Two vertically arranged nodes can also snap to a configurable fixed boundary gap. The default is 30 node-space units, and the candidate is valid only when the two boxes overlap horizontally.

### Interaction

- Ordinary `G` movement starts Smart Snap while the add-on is enabled.
- Node placement started from the `Shift + A` menu uses the same Smart Snap operator.
- A newly created node remains pending until Blender reports nonzero rendered dimensions; zero-size geometry is never used as a snap box.
- `Shift + D` uses Blender's native duplicate operator, then starts Smart Snap on the duplicated selection.
- Dragging an expanded or collapsed node by its title or body uses the same Smart Snap operator. Narrow left and right edge strips are excluded so socket linking remains usable.
- Collapsed nodes use live rendered dimensions plus a collapsed-state canvas offset. Expanded nodes do not use Node Wrangler highlight-outline offsets.
- Snap activation distance is stored in screen pixels and converted through both the current View2D scale and the measured node-geometry scale.
- Mouse coordinates, normalized node boxes, and guide drawing are converted through the same measured geometry scale.
- Alignment and spacing are solved independently for the horizontal and vertical axes.
- One alignment candidate collects every target that exposes the same snapped boundary, so a single guide represents the full aligned row or column.
- `X` and `Y` constraints disable candidates on the other axis.
- Alignment and spacing guides use solid centers with faded ends.
- A selected Frame moves its descendants through Blender parenting; selected descendants are not translated twice.
- Movement deltas are calculated in absolute canvas coordinates but written through each movement root's local `location`, which is the reliable writable coordinate for Frames.
- Nodes inside an unselected Frame compare against siblings in the same parent context.
- Nodes may compare against targets across Frame boundaries. A moving node's own ancestor Frames are excluded, while nodes inside other Frames remain valid targets.
- Child movement is solved in absolute canvas coordinates and converted back through the parent Frame's current absolute position on every update, preventing drift when Blender auto-resizes the Frame.
