from setuptools import setup, Extension
import numpy as np

# C extension for quads rendering
_quads_ext = Extension(
    "ni._ni_core._quads",
    sources=["src/ni/_ni_core/_quads.c"],
    include_dirs=[np.get_include()],
    extra_compile_args=["-O2"] if __import__("sys").platform != "win32" else ["/O2"],
)

setup(
    ext_modules=[_quads_ext],
)
