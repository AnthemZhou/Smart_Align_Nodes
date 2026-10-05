import bpy

from .preferences import get_preferences, draw_arrange_hint, draw_snap_settings, draw_layout_settings


class SMART_ALIGN_NODES_PT_sidebar(bpy.types.Panel):
    bl_label = "Smart Align Nodes"
    bl_idname = "SMART_ALIGN_NODES_PT_sidebar"
    bl_space_type = "NODE_EDITOR"
    bl_region_type = "UI"
    bl_category = "Smart Align"

    def draw(self, context):
        layout = self.layout
        draw_arrange_hint(layout, compact=True)
        preferences = get_preferences(context)
        if preferences is not None:
            settings = layout.column(align=True)
            draw_snap_settings(settings, preferences)

        layout.separator()
        layout.operator("smart_align_nodes.auto_layout", icon="NODETREE")
        if preferences is not None:
            draw_layout_settings(layout, preferences, compact=True)
        layout.operator("smart_align_nodes.debug_selected", icon="INFO")


classes = (SMART_ALIGN_NODES_PT_sidebar,)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
