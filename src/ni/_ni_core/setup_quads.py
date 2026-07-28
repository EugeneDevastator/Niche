# setup_quads.py
# python setup_quads.py build_ext --inplace
from setuptools import setup, Extension
import sys

ext = Extension(
    "_quads",
    sources=["_quads.c"],
    # no library_dirs, no libraries — zero external deps
    extra_compile_args=["/O2"] if sys.platform == "win32" else ["-O2"],
)

setup(name="_quads", ext_modules=[ext])
