# _ni_core/sdf_char_renderer.py
import os
import math
import numpy as np
import pyray as rl
import raylib as _raylib
from raylib._raylib_cffi import ffi as _ffi, lib as _lib
import _quads
from .layer import CH_CHAR, CH_FG, CH_BG, CH_STYLE, CH_GEO

ATLAS_GLYPH_SIZE = 24
SDF_PADDING      = 12

ASCII_BASE  = 32
ASCII_COUNT = 95

CP437_UNICODE = [
    0x00C7,0x00FC,0x00E9,0x00E2,0x00E4,0x00E0,0x00E5,0x00E7,
    0x00EA,0x00EB,0x00E8,0x00EF,0x00EE,0x00EC,0x00C4,0x00C5,
    0x00C9,0x00E6,0x00C6,0x00F4,0x00F6,0x00F2,0x00FB,0x00F9,
    0x00FF,0x00D6,0x00DC,0x00A2,0x00A3,0x00A5,0x20A7,0x0192,
    0x00E1,0x00ED,0x00F3,0x00FA,0x00F1,0x00D1,0x00AA,0x00BA,
    0x00BF,0x2310,0x00AC,0x00BD,0x00BC,0x00A1,0x00AB,0x00BB,
    0x2591,0x2592,0x2593,0x2502,0x2524,0x2561,0x2562,0x2556,
    0x2555,0x2563,0x2551,0x2557,0x255D,0x255C,0x255B,0x2510,
    0x2514,0x2534,0x252C,0x251C,0x2500,0x253C,0x255E,0x255F,
    0x255A,0x2554,0x2569,0x2566,0x2560,0x2550,0x256C,0x2567,
    0x2568,0x2564,0x2565,0x2559,0x2558,0x2552,0x2553,0x256B,
    0x256A,0x2518,0x250C,0x2588,0x2584,0x258C,0x2590,0x2580,
    0x03B1,0x00DF,0x0393,0x03C0,0x03A3,0x03C3,0x00B5,0x03C4,
    0x03A6,0x0398,0x03A9,0x03B4,0x221E,0x03C6,0x03B5,0x2229,
    0x2261,0x00B1,0x2265,0x2264,0x2320,0x2321,0x00F7,0x2248,
    0x00B0,0x2219,0x00B7,0x221A,0x207F,0x00B2,0x25A0,0x00A0,
]

_CP_TABLE_SIZE   = 0x2700
_FONT_PATH       = "C:/Windows/Fonts/consola.ttf"
_EDGE_WIDTH      = 0.04
_VERT_FLOATS     = 16
_VERTS_PER_QUAD  = 4
_ATLAS_DUMP_PATH = "rebaked_atlas.png"

_FMT_GRAY       = 1
_FMT_GRAY_ALPHA = 2
_FMT_RGBA       = 7

_staging     = None
_staging_cap = 0


def _ensure_staging(n_quads):
    global _staging, _staging_cap
    if n_quads <= _staging_cap:
        return
    cap = max(n_quads + 1024, 4096)
    _staging     = np.empty((cap * _VERTS_PER_QUAD, _VERT_FLOATS), dtype=np.float32)
    _staging_cap = cap


def _image_to_numpy_gray(img):
    w   = img.width
    h   = img.height
    fmt = img.format
    print(f"[sdf] old atlas format={fmt} w={w} h={h}")
    ptr = _ffi.cast("unsigned char *", img.data)
    if fmt == _FMT_GRAY:
        size = w * h
        buf  = np.frombuffer(_ffi.buffer(ptr, size), dtype=np.uint8).copy()
        return buf.reshape(h, w)
    elif fmt == _FMT_GRAY_ALPHA:
        size = w * h * 2
        buf  = np.frombuffer(_ffi.buffer(ptr, size), dtype=np.uint8).copy()
        return buf.reshape(h, w, 2)[:, :, 1]
    elif fmt == _FMT_RGBA:
        size = w * h * 4
        buf  = np.frombuffer(_ffi.buffer(ptr, size), dtype=np.uint8).copy()
        return buf.reshape(h, w, 4)[:, :, 3]
    else:
        size = w * h
        buf  = np.frombuffer(_ffi.buffer(ptr, size), dtype=np.uint8).copy()
        return buf.reshape(h, w)


def _scan_metrics(glyphs, recs, count):
    min_offsetY_across_glyphs  =  999999
    max_bottom_across_glyphs   = -999999
    max_bitmap_w               = 0
    max_offsetX                = -999999
    min_offsetX                =  999999
    for i in range(count):
        gi  = glyphs[i]
        rec = recs[i]
        oy  = int(gi.offsetY)
        ox  = int(gi.offsetX)
        bw  = int(rec.width)
        bh  = int(rec.height)
        bottom = oy + bh
        if oy     < min_offsetY_across_glyphs:  min_offsetY_across_glyphs = oy
        if bottom > max_bottom_across_glyphs:   max_bottom_across_glyphs  = bottom
        if bw     > max_bitmap_w:               max_bitmap_w  = bw
        if ox     > max_offsetX:                max_offsetX   = ox
        if ox     < min_offsetX:                min_offsetX   = ox
    ascent_px  = max(0, -min_offsetY_across_glyphs)
    descent_px = max(0, max_bottom_across_glyphs)
    cell_w                  = max_bitmap_w + 2 * SDF_PADDING
    cell_h                  = ascent_px + descent_px + 2 * SDF_PADDING
    baseline_row_in_cell    = SDF_PADDING + ascent_px
    print(f"[sdf] scan: min_offsetY={min_offsetY_across_glyphs} max_bottom={max_bottom_across_glyphs} max_bw={max_bitmap_w}")
    print(f"[sdf] scan: offsetX range [{min_offsetX}, {max_offsetX}]")
    print(f"[sdf] metrics: ascent={ascent_px} descent={descent_px} "
          f"cell={cell_w}x{cell_h} baseline_row_in_cell={baseline_row_in_cell}")
    for i in range(min(8, count)):
        gi  = glyphs[i]
        rec = recs[i]
        print(f"  glyph[{i}] cp={hex(gi.value)} ox={gi.offsetX} oy={gi.offsetY} "
              f"bmp={int(rec.width)}x{int(rec.height)}")
    return ascent_px, descent_px, cell_w, cell_h, baseline_row_in_cell


def _build_rebaked_atlas(glyphs, old_recs, old_np, count,
                         ascent_px, descent_px, cell_w, cell_h, baseline_row_in_cell):
    cols_n  = math.ceil(math.sqrt(count))
    rows_n  = math.ceil(count / cols_n)
    atlas_w = cols_n * cell_w
    atlas_h = rows_n * cell_h
    print(f"[sdf] rebake: cell={cell_w}x{cell_h} grid={cols_n}x{rows_n} "
          f"atlas={atlas_w}x{atlas_h}")
    atlas_np = np.zeros((atlas_h, atlas_w), dtype=np.uint8)
    new_recs = []
    src_h, src_w = old_np.shape
    for i in range(count):
        gi  = glyphs[i]
        rec = old_recs[i]
        gw  = int(rec.width)
        gh  = int(rec.height)
        ox  = int(gi.offsetX)
        oy  = int(gi.offsetY)
        cell_col = i % cols_n
        cell_row = i // cols_n
        cell_x   = cell_col * cell_w
        cell_y   = cell_row * cell_h
        sx = int(rec.x)
        sy = int(rec.y)
        dst_glyph_x = cell_x + SDF_PADDING + ox
        dst_glyph_y = cell_y + baseline_row_in_cell + oy
        src_ok = (sx >= 0 and sy >= 0 and
                  sx + gw <= src_w and sy + gh <= src_h)
        if not src_ok:
            print(f"[sdf] glyph {i} cp={hex(gi.value)} src OOB")
            new_recs.append((float(cell_x), float(cell_y),
                             float(cell_w), float(cell_h)))
            continue
        if (dst_glyph_x < cell_x or dst_glyph_y < cell_y or
                dst_glyph_x + gw > cell_x + cell_w or
                dst_glyph_y + gh > cell_y + cell_h):
            print(f"[sdf] glyph {i} cp={hex(gi.value)} dst OOB "
                  f"dx={dst_glyph_x} dy={dst_glyph_y} gw={gw} gh={gh} "
                  f"cell=({cell_x},{cell_y}) {cell_w}x{cell_h}")
            dst_glyph_x = max(cell_x, min(cell_x + cell_w - gw, dst_glyph_x))
            dst_glyph_y = max(cell_y, min(cell_y + cell_h - gh, dst_glyph_y))
        atlas_np[dst_glyph_y:dst_glyph_y+gh, dst_glyph_x:dst_glyph_x+gw] = \
            old_np[sy:sy+gh, sx:sx+gw]
        new_recs.append((float(cell_x), float(cell_y),
                         float(cell_w), float(cell_h)))
    return atlas_np, new_recs


def _upload_gray_alpha_numpy(np_gray):
    h, w   = np_gray.shape
    ga     = np.stack([np_gray, np_gray], axis=2).reshape(h, w * 2)
    raw    = ga.tobytes()
    nbytes = len(raw)
    c_buf  = _ffi.new("unsigned char[]", nbytes)
    _ffi.buffer(c_buf, nbytes)[:] = raw
    img         = _ffi.new("Image *")
    img.data    = c_buf
    img.width   = w
    img.height  = h
    img.mipmaps = 1
    img.format  = _raylib.PIXELFORMAT_UNCOMPRESSED_GRAY_ALPHA
    tex = _raylib.LoadTextureFromImage(img[0])
    return tex, c_buf


def _dump_atlas_png(np_arr, path):
    h, w   = np_arr.shape
    nbytes = w * h
    c_buf  = _ffi.new("unsigned char[]", nbytes)
    _ffi.buffer(c_buf, nbytes)[:] = np_arr.tobytes()
    img         = _ffi.new("Image *")
    img.data    = c_buf
    img.width   = w
    img.height  = h
    img.mipmaps = 1
    img.format  = _raylib.PIXELFORMAT_UNCOMPRESSED_GRAYSCALE
    _raylib.ExportImage(img[0], path.encode())
    print(f"[sdf] atlas dumped -> {path}")


def _load_and_rebake(path, codepoints_list):
    FONT_SDF = 2
    with open(path, "rb") as f:
        raw = f.read()
    c_data = _ffi.new("unsigned char[]", raw)
    count  = len(codepoints_list)
    cp_arr = _ffi.new("int[]", codepoints_list)
    glyphs = _raylib.LoadFontData(c_data, len(raw), ATLAS_GLYPH_SIZE,
                                  cp_arr, count, FONT_SDF)
    if not glyphs:
        return None, 0, 0, 0, None
    recs_out  = _ffi.new("Rectangle *[1]")
    old_atlas = _raylib.GenImageFontAtlas(glyphs, recs_out, count,
                                          ATLAS_GLYPH_SIZE, SDF_PADDING, 1)
    old_recs  = recs_out[0]
    old_np = _image_to_numpy_gray(old_atlas)
    _raylib.UnloadImage(old_atlas)
    ascent_px, descent_px, cell_w, cell_h, baseline_row_in_cell = \
        _scan_metrics(glyphs, old_recs, count)
    new_np, new_recs_list = _build_rebaked_atlas(
        glyphs, old_recs, old_np, count,
        ascent_px, descent_px, cell_w, cell_h, baseline_row_in_cell)
    _dump_atlas_png(new_np, _ATLAS_DUMP_PATH)
    tex, c_buf_ref = _upload_gray_alpha_numpy(new_np)
    _raylib.SetTextureFilter(tex, _raylib.TEXTURE_FILTER_BILINEAR)
    for i, (rx, ry, rw, rh) in enumerate(new_recs_list):
        old_recs[i].x      = rx
        old_recs[i].y      = ry
        old_recs[i].width  = rw
        old_recs[i].height = rh
    for i in range(count):
        glyphs[i].offsetX = 0
        glyphs[i].offsetY = 0
    font = _ffi.new("Font *")
    font.baseSize     = ATLAS_GLYPH_SIZE
    font.glyphCount   = count
    font.glyphPadding = SDF_PADDING
    font.glyphs       = glyphs
    font.recs         = old_recs
    font.texture      = tex
    return font, cell_w, cell_h, baseline_row_in_cell, c_buf_ref


def _fill_quads(out, cell_top_x, cell_top_y, scale_x, scale_y,
                atlas_idx_f, fg_r, fg_g, fg_b, fg_a,
                bg_r, bg_g, bg_b, bg_a,
                bold_u8, mode_f, skew_u8):
    n = len(cell_top_x)
    v = out.reshape(n, 4, _VERT_FLOATS)
    v[:, :, 0]  = cell_top_x[:, None]
    v[:, :, 1]  = cell_top_y[:, None]
    v[:, :, 2]  = atlas_idx_f[:, None]
    v[:, :, 3]  = fg_r[:, None]
    v[:, :, 4]  = fg_g[:, None]
    v[:, :, 5]  = fg_b[:, None]
    v[:, :, 6]  = fg_a[:, None]
    v[:, :, 7]  = bg_r[:, None]
    v[:, :, 8]  = bg_g[:, None]
    v[:, :, 9]  = bg_b[:, None]
    v[:, :, 10] = bg_a[:, None]
    v[:, :, 11] = bold_u8[:, None]
    v[:, :, 12] = mode_f
    v[:, :, 13] = skew_u8[:, None]
    v[:, :, 14] = scale_x[:, None]
    v[:, :, 15] = scale_y[:, None]


class SDFCharRenderer:

    def __init__(self):
        self._font               = None
        self._c_buf_ref          = None
        self._cp_idx_lut         = np.full(_CP_TABLE_SIZE, -1, dtype=np.int32)
        self._uv                 = None
        self._cell_w_atlas       = 1
        self._cell_h_atlas       = 1
        self._baseline_row_in_cell = 0
        self._ascent_px          = 0
        self._descent_px         = 0
        self._vp_w = 0.0
        self._vp_h = 0.0

    def init(self, vp_w: float, vp_h: float):
        self._vp_w = vp_w
        self._vp_h = vp_h
        if not os.path.exists(_FONT_PATH):
            return
        ascii_cps   = list(range(ASCII_BASE, ASCII_BASE + ASCII_COUNT))
        ascii_set   = set(ascii_cps)
        cp437_extra = [cp for cp in CP437_UNICODE if cp not in ascii_set]
        all_cps     = ascii_cps + cp437_extra
        font, cell_w, cell_h, baseline_row_in_cell, c_buf_ref = \
            _load_and_rebake(_FONT_PATH, all_cps)
        if font is None:
            return
        self._font                 = font
        self._c_buf_ref            = c_buf_ref
        self._cell_w_atlas         = cell_w
        self._cell_h_atlas         = cell_h
        self._baseline_row_in_cell = baseline_row_in_cell
        self._ascent_px            = baseline_row_in_cell - SDF_PADDING
        self._descent_px           = cell_h - baseline_row_in_cell - SDF_PADDING
        self._uv                   = self._build_uv_lookup(font, len(all_cps))

        for i, cp in enumerate(all_cps):
            if cp < _CP_TABLE_SIZE:
                self._cp_idx_lut[cp] = i

    def set_viewport(self, vp_w: float, vp_h: float):
        self._vp_w = vp_w
        self._vp_h = vp_h

    def _build_uv_lookup(self, font, count):
        tw = float(font.texture.width)
        th = float(font.texture.height)
        uv = np.zeros((count, 4), dtype=np.float32)
        for i in range(font.glyphCount):
            rec = font.recs[i]
            if i < count:
                uv[i, 0] = rec.x / tw
                uv[i, 1] = rec.y / th
                uv[i, 2] = (rec.x + rec.width)  / tw
                uv[i, 3] = (rec.y + rec.height) / th
        return uv

    def shutdown(self):
        if self._font:
            _raylib.UnloadTexture(self._font.texture)
        _quads.shutdown_gl()

    # sdf_char_renderer.py  — render_view only, rest of file unchanged

    def render_view(self, view_u8, view_cp, base_x, base_y, sx_f, sy_f, cw, ch, draw_size):
        if self._font is None:
            return

        rows, cols = view_cp.shape
        n = rows * cols

        flat_cp    = view_cp.ravel().astype(np.int32)
        clipped    = np.clip(flat_cp, 0, _CP_TABLE_SIZE - 1)
        atlas_idxs = self._cp_idx_lut[clipped].astype(np.float32)  # int32->float32, required

        fg_data  = view_u8[:, :, CH_FG].reshape(n, 4)    # uint8, no cast
        bg_data  = view_u8[:, :, CH_BG].reshape(n, 4)    # uint8, no cast
        st_data  = view_u8[:, :, CH_STYLE].reshape(n, 4)
        bold_u8  = st_data[:, 0]   # uint8
        skew_u8  = st_data[:, 1]   # uint8

        # already float32 from _decode_geo, ravel is a view not a copy
        scale_x    = sx_f.ravel()
        scale_y    = sy_f.ravel()
        cell_top_x = base_x.ravel()
        cell_top_y = base_y.ravel()

        _default_fg = np.uint8(30)
        has_fg = fg_data[:, 3] > 0
        r_arr = np.where(has_fg, fg_data[:, 0], _default_fg)
        g_arr = np.where(has_fg, fg_data[:, 1], _default_fg)
        b_arr = np.where(has_fg, fg_data[:, 2], _default_fg)
        a_arr = np.where(has_fg, fg_data[:, 3], np.uint8(255))

        total_quads = n + n
        _ensure_staging(total_quads)
        stg = _staging

        _fill_quads(
            stg[0 : n*4],
            cell_top_x, cell_top_y,
            scale_x, scale_y,
            np.full(n, -1.0, dtype=np.float32),
            np.zeros(n, dtype=np.float32),
            np.zeros(n, dtype=np.float32),
            np.zeros(n, dtype=np.float32),
            np.zeros(n, dtype=np.float32),
            bg_data[:, 0], bg_data[:, 1], bg_data[:, 2], bg_data[:, 3],
            np.zeros(n, dtype=np.float32),
            0.0,
            skew_u8,
        )

        _fill_quads(
            stg[n*4 : n*8],
            cell_top_x, cell_top_y,
            scale_x, scale_y,
            atlas_idxs,
            r_arr, g_arr, b_arr, a_arr,
            bg_data[:, 0], bg_data[:, 1], bg_data[:, 2], bg_data[:, 3],
            bold_u8,
            1.0,
            skew_u8,
        )

        _quads.draw_sdf_quads(
            stg,
            total_quads,
            int(self._font.texture.id),
            self._vp_w, self._vp_h,
            _EDGE_WIDTH,
            float(cw), float(ch), float(draw_size),
            float(self._cell_w_atlas), float(self._cell_h_atlas),
            float(self._baseline_row_in_cell),
            float(self._ascent_px), float(self._descent_px),
            float(SDF_PADDING),
            self._uv
        )

