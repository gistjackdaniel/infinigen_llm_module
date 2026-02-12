# Lazy import of blender and random to allow module import outside Blender
# Import them when needed: from infinigen.core.util import blender as butil
from .math import FixedSeed


# Lazy import for blender and random modules
def __getattr__(name):
    if name == "butil":
        from . import blender as butil

        return butil
    elif name == "random_general":
        from .random import random_general

        return random_general
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
