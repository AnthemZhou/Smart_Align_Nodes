# Changelog

## v0.4.2 (Unreleased)

### 中文

- 将维护者改为 `Anthem_周圣宇`。
- 在插件偏好设置中增加 B站、小红书、飞书和 GitHub 按钮。
- 校准 Reroute 到 socket 的首行中心高度。
- 等待新建节点生成有效渲染尺寸后再进行吸附计算。
- 增加 Node Console 创建后移动流程的兼容桥接。
- 增加默认值为 30 的可配置纵向节点间距。
- 改用局部 `location` 写入节点位移，修复 Frame 无法移动的问题。
- 允许 Frame 内外节点互相作为边界和 socket 吸附目标。
- 排除移动节点自己的祖先 Frame，避免子节点被父 Frame 边界干扰。
- 根据父 Frame 的实时绝对坐标换算子节点局部位置，修复 Frame 自动缩放时的累积漂移。

### English

- Change the maintainer to `Anthem_周圣宇`.
- Add Bilibili, Xiaohongshu, Feishu, and GitHub buttons to add-on preferences.
- Calibrate the first-row center used for Reroute-to-socket snapping.
- Wait for valid rendered dimensions before snapping a newly created node.
- Add a compatibility bridge for Node Console post-creation movement.
- Add a configurable default vertical node gap of 30.
- Write movement through local `location` coordinates to fix Frame movement.
- Allow nodes inside and outside Frames to act as boundary and socket snap targets for each other.
- Exclude a moving node's own ancestor Frames from snap targets.
- Convert child positions against the parent Frame's live absolute position to prevent cumulative drift while the Frame auto-resizes.

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
