import bpy

from .context import selected_nodes_from_context
from .debug import build_debug_report, write_report_to_text_block


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

        report = build_debug_report(tree, nodes)
        write_report_to_text_block(bpy, report)
        print(report)

        try:
            context.window_manager.clipboard = report
            suffix = " Copied to clipboard."
        except Exception:
            suffix = ""

        self.report({"INFO"}, f"Debugged {len(nodes)} selected node(s).{suffix}")
        return {"FINISHED"}


classes = (
    SMART_ALIGN_NODES_OT_debug_selected,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
