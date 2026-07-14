import bpy
from bpy.props import BoolProperty

from .context import selected_nodes_from_context
from .debug import (
    build_debug_report,
    collect_runtime_info,
    node_kind_flags,
    write_report_to_text_block,
)
from .geometry import node_box, snap_geometry
from .preferences import get_preferences
from .snapping import find_snaps, guide_segments


class SMART_ALIGN_NODES_OT_debug_selected(bpy.types.Operator):
    bl_idname = "smart_align_nodes.debug_selected"
    bl_label = "Debug Selected Nodes"
    bl_description = "Write selected node geometry, sockets, and links to Smart Align Debug"
    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, context):
        tree, _nodes = selected_nodes_from_context(context)
        return tree is not None

    def execute(self, context):
        tree, nodes = selected_nodes_from_context(context)
        if tree is None:
            self.report({"WARNING"}, "No node tree found.")
            return {"CANCELLED"}

        runtime_info = collect_runtime_info(context, bpy)
        report = build_debug_report(tree, nodes, runtime_info)
        write_report_to_text_block(bpy, report)
        print(report)

        try:
            context.window_manager.clipboard = report
            suffix = " Copied to clipboard."
        except Exception:
            suffix = ""

        self.report({"INFO"}, f"Debugged {len(nodes)} selected node(s).{suffix}")
        return {"FINISHED"}


def _window_region(area):
    for region in getattr(area, "regions", []):
        if getattr(region, "type", None) == "WINDOW":
            return region
    return None


def _event_canvas_position(event, region, geometry_scale):
    region_x = event.mouse_x - region.x
    region_y = event.mouse_y - region.y
    view_x, view_y = region.view2d.region_to_view(region_x, region_y)
    return view_x / geometry_scale, view_y / geometry_scale


def _view_scale(region):
    origin = region.view2d.view_to_region(0.0, 0.0, clip=False)
    x_sample = region.view2d.view_to_region(100.0, 0.0, clip=False)
    y_sample = region.view2d.view_to_region(0.0, 100.0, clip=False)
    scale_x = abs(float(x_sample[0]) - float(origin[0])) / 100.0
    scale_y = abs(float(y_sample[1]) - float(origin[1])) / 100.0
    return max(scale_x, 0.0001), max(scale_y, 0.0001)


def _drag_hits_node(event, region, nodes, geometry_scale):
    x, y = _event_canvas_position(event, region, geometry_scale)
    for node in nodes:
        box = node_box(node, geometry_scale)
        if box is None:
            continue
        flags = node_kind_flags(node)
        if flags["is_reroute"]:
            padding = 6.0
            if (
                box.left - padding <= x <= box.right + padding
                and box.bottom - padding <= y <= box.top + padding
            ):
                return True
            continue
        if not (box.left <= x <= box.right and box.bottom <= y <= box.top):
            continue
        edge_margin = min(8.0, box.width * 0.08)
        if box.left + edge_margin <= x <= box.right - edge_margin:
            return True
    return False


class _SmartMoveMixin:
    _draw_handle = None
    @classmethod
    def poll(cls, context):
        tree, nodes = selected_nodes_from_context(context)
        return tree is not None and bool(nodes)

    def invoke(self, context, event):
        tree, selected_nodes = selected_nodes_from_context(context)
        area = getattr(context, "area", None)
        region = _window_region(area)
        if tree is None or not selected_nodes or area is None or region is None:
            self.report({"WARNING"}, "Smart Snap requires selected nodes in a node editor.")
            return {"CANCELLED"}

        roots, moving_box, targets, geometry_scale = snap_geometry(
            tree, selected_nodes
        )
        if not roots:
            self.report({"WARNING"}, "Selected node geometry is not ready.")
            return {"CANCELLED"}

        fallback_scale = float(getattr(context.preferences.system, "dpi", 72)) / 72.0
        geometry_scale = max(float(geometry_scale or fallback_scale), 0.0001)
        if moving_box is None and not self.remove_on_cancel:
            self.report({"WARNING"}, "Selected node geometry is not ready.")
            return {"CANCELLED"}
        drag_invocation = getattr(self, "_force_drag_invocation", False)
        if drag_invocation and not _drag_hits_node(
            event, region, roots, geometry_scale
        ):
            return {"PASS_THROUGH"}

        self._tree = tree
        self._area = area
        self._region = region
        self._roots = roots
        self._moving_box = moving_box
        self._targets = targets
        self._selected_nodes = list(selected_nodes)
        self._geometry_pending = moving_box is None
        self._geometry_scale = geometry_scale
        self._confirm_on_release = drag_invocation
        self._cancel_nodes = list(selected_nodes) if self.remove_on_cancel else []
        self._initial_locations = {
            id(node): (
                float(node.location_absolute.x),
                float(node.location_absolute.y),
            )
            for node in roots
        }
        self._initial_mouse = _event_canvas_position(
            event, region, self._geometry_scale
        )
        self._axis_constraint = None
        self._guide_segments = []

        self._draw_handle = bpy.types.SpaceNodeEditor.draw_handler_add(
            self._draw_guides,
            (),
            "WINDOW",
            "POST_PIXEL",
        )
        context.window_manager.modal_handler_add(self)
        area.tag_redraw()
        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        if context.area != self._area:
            return self._cancel(context)

        if event.type in {"ESC", "RIGHTMOUSE", "WINDOW_DEACTIVATE"}:
            return self._cancel(context)

        if event.type == "LEFTMOUSE":
            confirm_value = "RELEASE" if self._confirm_on_release else "PRESS"
            if event.value == confirm_value:
                return self._finish(context)

        if event.type in {"RET", "NUMPAD_ENTER", "SPACE"}:
            if event.value == "PRESS":
                return self._finish(context)

        if event.type in {"X", "Y"} and event.value == "PRESS":
            self._axis_constraint = event.type.lower()
            self._update(context, event)
            return {"RUNNING_MODAL"}

        if event.type in {
            "MOUSEMOVE",
            "INBETWEEN_MOUSEMOVE",
            "LEFT_ALT",
            "RIGHT_ALT",
        }:
            self._update(context, event)
            return {"RUNNING_MODAL"}

        if event.type in {
            "MIDDLEMOUSE",
            "WHEELUPMOUSE",
            "WHEELDOWNMOUSE",
            "WHEELINMOUSE",
            "WHEELOUTMOUSE",
            "TRACKPADPAN",
            "TRACKPADZOOM",
        }:
            return {"PASS_THROUGH"}

        return {"RUNNING_MODAL"}

    def _update(self, context, event):
        if self._geometry_pending:
            roots, moving_box, targets, geometry_scale = snap_geometry(
                self._tree, self._selected_nodes
            )
            if moving_box is None:
                self._area.tag_redraw()
                return
            self._roots = roots
            self._moving_box = moving_box
            self._targets = targets
            self._geometry_scale = max(
                float(geometry_scale or self._geometry_scale), 0.0001
            )
            self._geometry_pending = False

        mouse_x, mouse_y = _event_canvas_position(
            event, self._region, self._geometry_scale
        )
        delta_x = mouse_x - self._initial_mouse[0]
        delta_y = mouse_y - self._initial_mouse[1]
        if self._axis_constraint == "x":
            delta_y = 0.0
        elif self._axis_constraint == "y":
            delta_x = 0.0

        moving = self._moving_box.translated(delta_x, delta_y)
        preferences = get_preferences(context)
        snap_distance = preferences.snap_distance if preferences is not None else 12
        equal_spacing = preferences.equal_spacing if preferences is not None else True
        show_guides = preferences.show_guides if preferences is not None else True
        scale_x, scale_y = _view_scale(self._region)

        if event.alt:
            result = None
            correction_x = 0.0
            correction_y = 0.0
        else:
            result = find_snaps(
                moving,
                self._targets,
                snap_distance / (scale_x * self._geometry_scale),
                snap_distance / (scale_y * self._geometry_scale),
                equal_spacing,
                self._axis_constraint,
            )
            correction_x = result.correction_x
            correction_y = result.correction_y

        final_delta_x = delta_x + correction_x
        final_delta_y = delta_y + correction_y
        for node in self._roots:
            initial_x, initial_y = self._initial_locations[id(node)]
            node.location_absolute.x = initial_x + final_delta_x
            node.location_absolute.y = initial_y + final_delta_y

        final_box = self._moving_box.translated(final_delta_x, final_delta_y)
        self._guide_segments = (
            guide_segments(result, final_box) if result is not None and show_guides else []
        )
        self._area.tag_redraw()

    def _restore_locations(self):
        for node in self._roots:
            initial_x, initial_y = self._initial_locations[id(node)]
            node.location_absolute.x = initial_x
            node.location_absolute.y = initial_y

    def _finish(self, context):
        self._cleanup()
        return {"FINISHED"}

    def _cancel(self, context):
        if self.remove_on_cancel:
            for node in self._cancel_nodes:
                try:
                    self._tree.nodes.remove(node)
                except (ReferenceError, RuntimeError):
                    pass
        else:
            self._restore_locations()
        self._cleanup()
        return {"CANCELLED"}

    def _cleanup(self):
        if self._draw_handle is not None:
            bpy.types.SpaceNodeEditor.draw_handler_remove(self._draw_handle, "WINDOW")
            self._draw_handle = None
        self._guide_segments = []
        if self._area is not None:
            self._area.tag_redraw()

    def _draw_guides(self):
        if not self._guide_segments or bpy.context.area != self._area:
            return

        import gpu
        from gpu_extras.batch import batch_for_shader

        shader = gpu.shader.from_builtin("POLYLINE_SMOOTH_COLOR")
        colors = {
            "alignment": (0.12, 0.82, 0.92, 0.95),
            "spacing": (1.0, 0.55, 0.12, 0.95),
        }
        try:
            gpu.state.blend_set("ALPHA")
            shader.bind()
            shader.uniform_float("viewportSize", gpu.state.viewport_get()[2:])
            shader.uniform_float("lineWidth", 1.5)
            for kind, color in colors.items():
                for segment in self._guide_segments:
                    if segment.kind != kind:
                        continue
                    start = self._region.view2d.view_to_region(
                        segment.start[0] * self._geometry_scale,
                        segment.start[1] * self._geometry_scale,
                        clip=False,
                    )
                    end = self._region.view2d.view_to_region(
                        segment.end[0] * self._geometry_scale,
                        segment.end[1] * self._geometry_scale,
                        clip=False,
                    )
                    if segment.fade:
                        inner_start = (
                            start[0] + (end[0] - start[0]) * 0.18,
                            start[1] + (end[1] - start[1]) * 0.18,
                        )
                        inner_end = (
                            start[0] + (end[0] - start[0]) * 0.82,
                            start[1] + (end[1] - start[1]) * 0.82,
                        )
                        coordinates = (start, inner_start, inner_end, end)
                        transparent = (*color[:3], 0.0)
                        vertex_colors = (transparent, color, color, transparent)
                    else:
                        coordinates = (start, end)
                        vertex_colors = (color, color)
                    batch = batch_for_shader(
                        shader,
                        "LINE_STRIP",
                        {"pos": coordinates, "color": vertex_colors},
                    )
                    batch.draw(shader)
        finally:
            gpu.state.blend_set("NONE")


class SMART_ALIGN_NODES_OT_move_with_snap(_SmartMoveMixin, bpy.types.Operator):
    bl_idname = "smart_align_nodes.move_with_snap"
    bl_label = "Move with Smart Snap"
    bl_description = "Move selected nodes with boundary and equal-spacing snapping"
    bl_options = {"REGISTER", "UNDO", "BLOCKING"}

    remove_on_cancel: BoolProperty(
        name="Remove on Cancel",
        default=False,
        options={"HIDDEN", "SKIP_SAVE"},
    )

    def invoke(self, context, event):
        self._force_drag_invocation = False
        return super().invoke(context, event)


class SMART_ALIGN_NODES_OT_drag_with_snap(_SmartMoveMixin, bpy.types.Operator):
    bl_idname = "smart_align_nodes.drag_with_snap"
    bl_label = "Drag with Smart Snap"
    bl_description = "Drag a node with boundary and equal-spacing snapping"
    bl_options = {"REGISTER", "UNDO", "BLOCKING"}

    remove_on_cancel: BoolProperty(
        name="Remove on Cancel",
        default=False,
        options={"HIDDEN", "SKIP_SAVE"},
    )

    def invoke(self, context, event):
        self._force_drag_invocation = True
        return super().invoke(context, event)


class SMART_ALIGN_NODES_OT_duplicate_move(bpy.types.Operator):
    bl_idname = "smart_align_nodes.duplicate_move"
    bl_label = "Duplicate with Smart Snap"
    bl_description = "Duplicate selected nodes and move them with Smart Snap"

    @classmethod
    def poll(cls, context):
        tree, nodes = selected_nodes_from_context(context)
        return tree is not None and bool(nodes)

    def invoke(self, context, event):
        window = context.window
        area = context.area
        region = context.region

        def duplicate_then_move():
            try:
                with bpy.context.temp_override(
                    window=window,
                    area=area,
                    region=region,
                ):
                    result = bpy.ops.node.duplicate("EXEC_DEFAULT")
                    if "FINISHED" in result:
                        bpy.ops.smart_align_nodes.move_with_snap(
                            "INVOKE_DEFAULT",
                            remove_on_cancel=True,
                        )
            except (ReferenceError, RuntimeError):
                pass
            return None

        bpy.app.timers.register(duplicate_then_move, first_interval=0.0)
        return {"FINISHED"}


classes = (
    SMART_ALIGN_NODES_OT_debug_selected,
    SMART_ALIGN_NODES_OT_move_with_snap,
    SMART_ALIGN_NODES_OT_drag_with_snap,
    SMART_ALIGN_NODES_OT_duplicate_move,
)

addon_keymaps = []
_NODE_ADD_PATCH_ATTRIBUTE = "_smart_align_nodes_original_invoke"
_NODE_ADD_CLASSES_ATTRIBUTE = "_smart_align_nodes_registered_classes"


def _node_add_invoke_with_snap(self, context, event):
    self.store_mouse_cursor(context, event)
    result = self.execute(context)
    if self.use_transform and "FINISHED" in result:
        move_result = bpy.ops.smart_align_nodes.move_with_snap(
            "INVOKE_DEFAULT",
            remove_on_cancel=True,
        )
        if "CANCELLED" in move_result:
            bpy.ops.node.translate_attach_remove_on_cancel("INVOKE_DEFAULT")
    return result


def _patch_node_add_transform():
    from bl_operators import node as node_operators

    NodeAddOperator = node_operators.NodeAddOperator

    if not hasattr(NodeAddOperator, _NODE_ADD_PATCH_ATTRIBUTE):
        setattr(
            NodeAddOperator,
            _NODE_ADD_PATCH_ATTRIBUTE,
            NodeAddOperator.invoke,
        )
    operator_classes = tuple(
        cls
        for cls in node_operators.classes
        if isinstance(cls, type)
        and issubclass(cls, NodeAddOperator)
        and cls is not NodeAddOperator
    )
    for cls in reversed(operator_classes):
        bpy.utils.unregister_class(cls)
    NodeAddOperator.invoke = _node_add_invoke_with_snap
    for cls in operator_classes:
        bpy.utils.register_class(cls)
    setattr(NodeAddOperator, _NODE_ADD_CLASSES_ATTRIBUTE, operator_classes)


def _restore_node_add_transform():
    from bl_operators.node import NodeAddOperator

    original = getattr(NodeAddOperator, _NODE_ADD_PATCH_ATTRIBUTE, None)
    if original is not None:
        operator_classes = getattr(
            NodeAddOperator, _NODE_ADD_CLASSES_ATTRIBUTE, ()
        )
        for cls in reversed(operator_classes):
            bpy.utils.unregister_class(cls)
        NodeAddOperator.invoke = original
        for cls in operator_classes:
            bpy.utils.register_class(cls)
        delattr(NodeAddOperator, _NODE_ADD_PATCH_ATTRIBUTE)
        if hasattr(NodeAddOperator, _NODE_ADD_CLASSES_ATTRIBUTE):
            delattr(NodeAddOperator, _NODE_ADD_CLASSES_ATTRIBUTE)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    keyconfig = bpy.context.window_manager.keyconfigs.addon
    if keyconfig is not None:
        keymap = keyconfig.keymaps.new(
            name="Node Editor",
            space_type="NODE_EDITOR",
            region_type="WINDOW",
        )
        keymap_item = keymap.keymap_items.new(
            SMART_ALIGN_NODES_OT_move_with_snap.bl_idname,
            "G",
            "PRESS",
        )
        addon_keymaps.append((keymap, keymap_item))
        drag_item = keymap.keymap_items.new(
            SMART_ALIGN_NODES_OT_drag_with_snap.bl_idname,
            "LEFTMOUSE",
            "CLICK_DRAG",
        )
        addon_keymaps.append((keymap, drag_item))
        duplicate_item = keymap.keymap_items.new(
            SMART_ALIGN_NODES_OT_duplicate_move.bl_idname,
            "D",
            "PRESS",
            shift=True,
        )
        addon_keymaps.append((keymap, duplicate_item))
    _patch_node_add_transform()


def unregister():
    _restore_node_add_transform()
    for keymap, keymap_item in addon_keymaps:
        keymap.keymap_items.remove(keymap_item)
    addon_keymaps.clear()

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
