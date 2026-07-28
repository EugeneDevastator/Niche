# _ni_core/_quads_init.py
import os
import sys
import ctypes

# shader files live in pylib/ (parent of _ni_core/)
_CORE_DIR   = os.path.dirname(os.path.abspath(__file__))
_PYLIB_DIR  = os.path.dirname(_CORE_DIR)
SHADER_DIR  = os.path.join(_PYLIB_DIR, "shaders")


def init_quads_ffi():
    import _quads
    from raylib._raylib_cffi import ffi, lib

    def addr(fn):
        return int(ffi.cast("uintptr_t", fn))

    _quads.init_ffi_ptrs(
        addr(lib.rlBegin),
        addr(lib.rlEnd),
        addr(lib.rlVertex2f),
        addr(lib.rlTexCoord2f),
        addr(lib.rlColor4f),
        addr(lib.rlSetTexture),
    )

    if sys.platform == "win32":
        import raylib._raylib_cffi as _cffi_mod
        _cffi_dir = os.path.dirname(_cffi_mod.__file__)

        _rl_dll = None
        for name in ["raylib.dll", "_raylib_cffi.pyd", "_raylib_cffi.dll"]:
            candidate = os.path.join(_cffi_dir, name)
            if os.path.exists(candidate):
                try:
                    _rl_dll = ctypes.CDLL(candidate)
                    break
                except OSError:
                    continue

        _gl_core = ctypes.WinDLL("opengl32.dll")

        try:
            _wgl_get = ctypes.WINFUNCTYPE(
                ctypes.c_void_p, ctypes.c_char_p
            )(("wglGetProcAddress", _gl_core))
        except Exception:
            _wgl_get = None

        def loader(name):
            bname = name.encode()
            if _rl_dll is not None:
                try:
                    fn  = getattr(_rl_dll, name)
                    v   = ctypes.cast(fn, ctypes.c_void_p).value
                    if v:
                        return v
                except AttributeError:
                    pass
            if _wgl_get:
                v = _wgl_get(bname)
                if v:
                    return v
            try:
                fn = getattr(_gl_core, name)
                v  = ctypes.cast(fn, ctypes.c_void_p).value
                if v:
                    return v
            except AttributeError:
                pass
            return 0
    else:
        _gl = ctypes.CDLL(ctypes.util.find_library("GL"))

        def loader(name):
            try:
                fn = getattr(_gl, name)
                return ctypes.cast(fn, ctypes.c_void_p).value or 0
            except AttributeError:
                return 0

    _quads.init_gl_ptrs(loader, SHADER_DIR)
