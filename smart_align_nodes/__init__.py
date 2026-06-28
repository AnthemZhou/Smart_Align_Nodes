bl_info = {
    "name": "Smart Align Nodes",
    "author": "Smart Align Nodes contributors",
    "version": (0, 3, 0),
    "blender": (4, 0, 0),
    "location": "Node Editor > Sidebar > Smart Align",
    "description": "Debug selected Blender node geometry, sockets, and links.",
    "category": "Node",
}

def register():
    from . import operators, ui

    operators.register()
    ui.register()


def unregister():
    from . import operators, ui

    ui.unregister()
    operators.unregister()
