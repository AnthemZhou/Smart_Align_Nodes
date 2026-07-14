# Smart Align Nodes

![Blender](https://img.shields.io/badge/Blender-4.0%2B-f5792a?logo=blender&logoColor=white)
![Version](https://img.shields.io/badge/version-0.4.2-blue)
![Category](https://img.shields.io/badge/category-Node%20Editor-555)
![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Windows%20%7C%20Linux-lightgrey)
![License](https://img.shields.io/badge/license-GPL--3.0-green)

维护者：Anthem_周圣宇<br>
版本：0.4.2

## 中文

Smart Align Nodes 是一个 Blender 节点编辑器对齐插件。启用插件后，移动、创建或复制节点时会自动检测节点边界和相等间距，并显示类似演示文稿软件的吸附参考线。插件不依赖 Blender 的网格量化吸附。

### 功能

- 按 `G` 移动节点时自动吸附。
- 从 `Shift + A` 菜单创建节点并移动时自动吸附。
- 兼容 Node Console 创建节点后的移动流程。
- 按 `Shift + D` 复制节点并移动时自动吸附。
- 使用鼠标左键拖动节点标题或主体区域时自动吸附。
- 支持左、右、上、下四条边界吸附，不使用中心吸附。
- 支持横向或纵向相等间距吸附。只有节点在另一方向具有实际重叠时才会激活。
- 支持可配置的默认纵向节点间距，默认值为 30 个节点坐标单位。
- 多选节点作为一个整体移动，不改变内部相对位置。
- 支持展开节点、折叠节点、Frame 和 Reroute 的独立几何规则。
- Frame 内外的节点可以互相作为边界和 socket 吸附目标。
- 子节点靠近 Frame 边界并触发 Frame 自动缩放时，会维持稳定的绝对移动位置。
- Reroute 在纵向移动时可以吸附到普通节点的 socket 高度候选。
- 青色参考线表示边界吸附，橙色测量线表示相等间距，线段首尾带有渐隐效果。
- 提供 `Debug Selected Nodes`，用于输出节点几何、Frame、Reroute、socket 和 link 数据。

### 安装

1. 从 release assets 下载 `Smart_Align_Nodes_v0.4.2.zip`。
2. 在 Blender 中打开 `编辑 > 偏好设置 > 插件`。
3. 点击 `安装...`，选择下载的 zip 文件。
4. 启用 `Smart Align Nodes`。

### 使用

1. 打开任意节点编辑器。
2. 选择一个或多个节点。
3. 按 `G`、使用 `Shift + A` 创建节点、按 `Shift + D` 复制节点，或直接用鼠标左键拖动节点。
4. 移动鼠标。进入吸附距离后，节点会自动对齐并显示参考线。
5. 点击鼠标左键或按 Enter 确认位置。

移动时按 `X` 或 `Y` 可以限制轴向。按住 `Alt/Option` 可以临时跳过吸附。

### 设置

- `吸附距离`（Snap Distance）：边界或间距候选在屏幕上的触发距离，单位为 px。默认值是 12 px，不是网格间距或节点间隔。
- `Vertical Gap`：两个节点上下排列且横向重叠时使用的默认边界间距，默认值为 30。
- `Equal Spacing`：启用相等间距吸附。
- `Show Guides`：显示吸附参考线。
- `Debug Selected Nodes`：将选中节点的诊断信息写入 Blender 文本块 `Smart Align Debug`，并输出到系统控制台。

### 说明

- Smart Snap 会在插件启用时接管节点编辑器中的普通 `G` 移动。禁用插件后会恢复 Blender 原生行为。
- Blender 的公开 Python API 不提供 socket 的最终画布绘制坐标。Reroute 到 socket 的吸附位置目前根据节点边界、socket 顺序和显示状态估算，不同自定义节点可能仍需继续校准。
- 鼠标拖动会覆盖节点内部的大部分区域。为避免影响连线操作，节点左右两侧靠近 socket 的窄区域不会启动拖动。
- 插件以普通 Blender 插件 zip 格式发布，开源协议为 GPL-3.0-only。

## English

Smart Align Nodes is an alignment add-on for the Blender Node Editor. Once enabled, it detects node boundaries and equal gaps while nodes are moved, created, or duplicated, then displays presentation-style snapping guides. Blender grid quantization is not required.

### Features

- Automatically snaps nodes during ordinary `G` movement.
- Automatically snaps newly created nodes while placing them from the `Shift + A` menu.
- Supports post-creation movement initiated by Node Console.
- Automatically snaps duplicated nodes during `Shift + D` placement.
- Automatically snaps while dragging a node by its title or body with the left mouse button.
- Supports left, right, top, and bottom boundary snapping without center snapping.
- Supports equal horizontal or vertical spacing. A spacing candidate activates only when the nodes genuinely overlap on the other axis.
- Supports a configurable default vertical node gap of 30 node-space units.
- Moves a multi-node selection as one group without changing its internal layout.
- Uses separate geometry rules for expanded nodes, collapsed nodes, Frames, and Reroutes.
- Allows nodes inside and outside Frames to act as boundary and socket snap targets for each other.
- Keeps child movement stable when approaching a Frame boundary causes the Frame to auto-resize.
- Lets a vertically moving Reroute snap to estimated socket-height candidates on normal nodes.
- Uses cyan boundary guides and orange spacing measurements with faded ends.
- Includes `Debug Selected Nodes` for node geometry, Frame, Reroute, socket, and link diagnostics.

### Install

1. Download `Smart_Align_Nodes_v0.4.2.zip` from the release assets.
2. In Blender, open `Edit > Preferences > Add-ons`.
3. Click `Install...`, then choose the downloaded zip file.
4. Enable `Smart Align Nodes`.

### Usage

1. Open any node editor.
2. Select one or more nodes.
3. Press `G`, create a node with `Shift + A`, duplicate with `Shift + D`, or drag a node directly with the left mouse button.
4. Move the pointer. The node snaps and displays a guide when a candidate enters the snap distance.
5. Click the left mouse button or press Enter to confirm.

Press `X` or `Y` during movement to constrain an axis. Hold `Alt/Option` to bypass snapping temporarily.

### Settings

- `Snap Distance`: the screen-space activation distance for boundary and spacing candidates, measured in px. The default 12 px is not a grid interval or node gap.
- `Vertical Gap`: the default boundary gap for vertically arranged nodes with horizontal overlap. The default value is 30.
- `Equal Spacing`: enables equal-spacing snapping.
- `Show Guides`: displays snapping guides.
- `Debug Selected Nodes`: writes selected-node diagnostics to the Blender text block `Smart Align Debug` and prints the same report to the system console.

### Notes

- Smart Snap replaces ordinary `G` movement in the Node Editor while the add-on is enabled. Disabling the add-on restores Blender native behavior.
- Blender's public Python API does not expose final canvas coordinates for sockets. Reroute-to-socket snapping currently estimates positions from node bounds, socket order, and visibility, so custom node types may still require calibration.
- Mouse dragging covers most of the node interior. Narrow strips near the left and right socket edges remain available for link interaction.
- The add-on is released as a regular Blender add-on zip under GPL-3.0-only.

See [LICENSE](LICENSE).
