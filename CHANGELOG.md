# Changelog

## v0.4.1

### 中文

- 将鼠标拖动吸附范围从节点标题扩展到节点主体区域，并保留 socket 两侧的连线操作空间。
- 修正折叠节点在画布上的整体绘制偏移，提高上边界和下边界吸附精度。
- 增加 Reroute 到普通节点 socket 高度候选的纵向吸附。
- 将 README 和 release note 改为中英文双语结构。
- 保留 `G`、`Shift + A`、`Shift + D`、四边界吸附、相等间距和调试报告功能。

### English

- Extend mouse-drag snapping from node titles to node body areas while keeping narrow socket-edge regions available for link interaction.
- Correct the canvas render offset of collapsed nodes to improve top and bottom boundary snapping.
- Add vertical Reroute snapping to estimated socket-height candidates on normal nodes.
- Use bilingual Chinese and English structures for the README and release notes.
- Preserve `G`, `Shift + A`, `Shift + D`, four-boundary snapping, equal spacing, and debug reports.

## v0.4.0

- Integrate Smart Snap into ordinary `G` movement and new-node placement.
- Add left, right, top, and bottom boundary snapping.
- Add Smart Snap when dragging nodes from their title area.
- Add Smart Snap after `Shift + D` duplication.
- Re-register Blender's Python node-add operators so `Shift + A` placement enters Smart Snap.
- Add equal-spacing snapping for insertion and sequence extension.
- Require real orthogonal overlap before activating equal-spacing snapping.
- Place spacing guides inside the common overlap region.
- Add screen-space thresholds and alignment or spacing guides with faded ends.
- Normalize mouse movement and guide drawing against Blender's measured UI scale.
- Normalize expanded and collapsed nodes from their live rendered dimensions.
- Remove Node Wrangler highlight-outline offsets from snap geometry.
- Extend alignment guides across every node on the same snapped boundary.
- Move multi-node selections as one group.
- Add Frame-aware movement roots and Reroute center snapping.
- Add axis constraints and temporary snap bypass.
- Add add-on submodule reloading after an overwrite update.
- Keep the `v0.3.1` debug report available.

## v0.3.1

- Add Blender version, display scale, editor region, and View2D diagnostics.
- Add observed geometry scale ratios and normalized node box candidates.
- Report Reroute nodes as center anchors with candidate collision boxes.
- Add Frame ancestry and selected movement roots.
- Expand Socket visibility and display-state diagnostics.
- Fix node-level link matching for Blender RNA wrapper objects.
- Keep all debug geometry read-only and label inferred values explicitly.

## v0.3.0

- Start the new Smart Align Nodes implementation from a clean design.
- Add a node editor sidebar panel.
- Add selected-node debug output.
- Add raw geometry, socket, link, Frame, and Reroute diagnostics.
- Add GPL-3.0 license.
- Add initial algorithm planning document.
