import importlib
import sys


bl_info = {
    "name": "Smart Align Nodes",
    "author": "Anthem_周圣宇",
    "version": (0, 4, 2),
    "blender": (4, 0, 0),
    "location": "Node Editor > Sidebar > Smart Align",
    "description": "Move Blender nodes with alignment and equal-spacing snapping.",
    "category": "Node",
}


MODULE_NAMES = (
    "context",
    "debug",
    "geometry",
    "snapping",
    "preferences",
    "operators",
    "ui",
)


def _load_modules(reload_existing):
    modules = {}
    for name in MODULE_NAMES:
        qualified_name = f"{__package__}.{name}"
        if qualified_name in sys.modules:
            module = sys.modules[qualified_name]
            if reload_existing:
                module = importlib.reload(module)
        else:
            module = importlib.import_module(qualified_name)
        modules[name] = module
    return modules


def register():
    modules = _load_modules(reload_existing=True)
    modules["preferences"].register()
    modules["operators"].register()
    modules["ui"].register()


def unregister():
    modules = _load_modules(reload_existing=False)
    modules["ui"].unregister()
    modules["operators"].unregister()
    modules["preferences"].unregister()
