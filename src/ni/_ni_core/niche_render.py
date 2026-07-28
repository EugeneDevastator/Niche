# _ni_core/niche_render.py
import numpy as np
import pyray as rl
import raylib as _raylib
from raylib._raylib_cffi import ffi as _ffi, lib as _lib
from typing import Optional, Callable
from .layer import (
    layer_blit, _clip_rect,
    CH_COUNT, CH_GEO, CH_BG, CH_FG, CH_CHAR,
    LYR_COUNT, LYR_UNDER, LYR_MAIN, LYR_OVER,
    make_layer,
)
from .sdf_char_renderer import SDFCharRenderer
from .niche_input import EventBus
from ._quads_init import init_quads_ffi
import _quads

DEFAULT_FONT_SIZE = 16
BASE_CELL_W = 8.0
BASE_CELL_H = 18.0

ZOOM_MIN = 0.025
ZOOM_MAX = 4.0

DATABUFFER_COLS = 4000
DATABUFFER_ROWS = 4000

LOD_GLYPH_MIN_PX = 4
_DIRTY_PAD       = 1
_SNAP_THRESHOLD_PX = 8.0

_LOD_SIZES = [
    (1, 2), (2, 3), (3, 5), (4, 7),
    (5, 9), (6, 11), (7, 13), (8, 14),
]

_INV32 = np.float32(1.0 / 32.0)
_INV64 = np.float32(1.0 / 64.0)


class DirtyTracker:
    def __init__(self):
        self._cells = set()
        self._full  = False

    def mark_full(self):
        self._full = True
        self._cells.clear()

    def mark_cell(self, col, row):
        if not self._full:
            self._cells.add((col, row))

    def mark_rect(self, col, row, w, h):
        if self._full: return
        if w * h > 512:
            self._full = True; self._cells.clear(); return
        for r in range(row, row + h):
            for c in range(col, col + w):
                self._cells.add((c, r))

    def is_dirty(self):
        return self._full or len(self._cells) > 0

    def consume_pixel_rects(self, cw_f, ch_f, vis_cols, vis_rows):
        if not self.is_dirty(): return
        full  = self._full
        cells = self._cells
        self._full  = False
        self._cells = set()
        vp_w = vis_cols * cw_f
        vp_h = vis_rows * ch_f
        if full:
            yield None; return
        rows = {}
        for (c, r) in cells:
            rows.setdefault(r, []).append(c)
        for r, cols in rows.items():
            cols.sort()
            run_start = run_end = cols[0]
            for c in cols[1:]:
                if c == run_end + 1:
                    run_end = c
                else:
                    yield _pad_rect(run_start, r, run_end - run_start + 1, 1,
                                    cw_f, ch_f, vp_w, vp_h)
                    run_start = run_end = c
            yield _pad_rect(run_start, r, run_end - run_start + 1, 1,
                            cw_f, ch_f, vp_w, vp_h)


def _pad_rect(col, row, w, h, cw_f, ch_f, vp_w, vp_h):
    px  = max(0.0,  (col - _DIRTY_PAD) * cw_f)
    py  = max(0.0,  (row - _DIRTY_PAD) * ch_f)
    px2 = min(vp_w, (col + w + _DIRTY_PAD) * cw_f)
    py2 = min(vp_h, (row + h + _DIRTY_PAD) * ch_f)
    return (px, py, px2 - px, py2 - py)


def _lod_cell_size(raw_zoom):
    raw_cw = BASE_CELL_W * raw_zoom
    if raw_cw >= float(len(_LOD_SIZES) + 1):
        return raw_cw, BASE_CELL_H * raw_zoom
    ipx = max(1, min(len(_LOD_SIZES), int(raw_cw)))
    cw, ch = _LOD_SIZES[ipx - 1]
    return float(cw), float(ch)


def _decode_geo(geo_u8, cw_f, ch_f):
    """
    geo_u8: uint8 (rows, cols, 4)
    Returns ox_px, oy_px, sx_f, sy_f — all float32 (rows, cols)
    """
    raw_ox = geo_u8[:, :, 0].astype(np.float32)
    raw_oy = geo_u8[:, :, 1].astype(np.float32)
    ox_f   = np.where(raw_ox == 0, np.float32(0.0), (raw_ox - 128.0) * _INV32)
    oy_f   = np.where(raw_oy == 0, np.float32(0.0), (raw_oy - 128.0) * _INV32)
    ox_px  = ox_f * cw_f
    oy_px  = oy_f * ch_f
    s2     = geo_u8[:, :, 2].astype(np.float32) * _INV64
    s3     = geo_u8[:, :, 3].astype(np.float32) * _INV64
    sx_f   = np.where(s2 == 0.0, np.float32(1.0), s2)
    sy_f   = np.where(s3 == 0.0, np.float32(1.0), s3)
    return ox_px, oy_px, sx_f, sy_f


class Renderer:

    def __init__(self, win_w=1280, win_h=720, title="renderer"):
        self._win_w  = win_w
        self._win_h  = win_h
        self._title  = title
        self._sdf    = SDFCharRenderer()
        self._zoom   = 1.0
        self._cell_w_f       = BASE_CELL_W
        self._cell_h_f       = BASE_CELL_H
        self._font_draw_size = float(DEFAULT_FONT_SIZE)
        self._fb     = None
        self._fb_tmp = None
        self._data   = None   # uint8
        self._chars  = None   # uint32
        self._layer_visible  = [True] * LYR_COUNT
        self._events  = EventBus()
        self._dirty   = DirtyTracker()

    def shift_texture(self, x, y, w, h,
                      shift_x, shift_y,
                      preserve_bound=True,
                      clear_freed=True):
        cw_f = self._cell_w_f
        ch_f = self._cell_h_f

        px   = int(x * cw_f);  py  = int(y * ch_f)
        pw   = int(w * cw_f);  ph  = int(h * ch_f)
        spx  = int(shift_x * cw_f)
        spy  = int(shift_y * ch_f)

        if preserve_bound:
            src_x = px + max(0, -spx)
            src_y = py + max(0, -spy)
            src_w = pw - abs(spx)
            src_h = ph - abs(spy)
            dst_x = src_x + spx
            dst_y = src_y + spy
        else:
            src_x = px; src_y = py
            src_w = pw; src_h = ph
            dst_x = px + spx; dst_y = py + spy

        if src_w <= 0 or src_h <= 0:
            return

        fb_h = self._fb.texture.height

        rl.begin_texture_mode(self._fb_tmp)
        rl.clear_background(rl.WHITE)
        src_rect = rl.Rectangle(float(src_x), float(fb_h - src_y - src_h),
                                float(src_w), float(-src_h))
        dst_rect = rl.Rectangle(0.0, 0.0, float(src_w), float(src_h))
        rl.draw_texture_pro(self._fb.texture, src_rect, dst_rect,
                            rl.Vector2(0, 0), 0.0, rl.WHITE)
        rl.end_texture_mode()

        rl.begin_texture_mode(self._fb)
        if clear_freed:
            rl.begin_scissor_mode(px, py, pw, ph)
            rl.draw_rectangle(px, py, pw, ph, rl.WHITE)
            rl.end_scissor_mode()

        blit_x = dst_x; blit_y = dst_y
        blit_w = src_w; blit_h = src_h
        uv_ox = 0;      uv_oy = 0
        if preserve_bound:
            clip_x0 = max(blit_x, px); clip_y0 = max(blit_y, py)
            clip_x1 = min(blit_x + blit_w, px + pw)
            clip_y1 = min(blit_y + blit_h, py + ph)
            if clip_x1 <= clip_x0 or clip_y1 <= clip_y0:
                rl.end_texture_mode()
                return
            uv_ox  = clip_x0 - blit_x; uv_oy = clip_y0 - blit_y
            blit_w = clip_x1 - clip_x0; blit_h = clip_y1 - clip_y0
            blit_x = clip_x0; blit_y = clip_y0

        tmp_h = self._fb_tmp.texture.height
        tmp_src = rl.Rectangle(float(uv_ox), float(tmp_h - uv_oy - blit_h),
                               float(blit_w), float(-blit_h))
        tmp_dst = rl.Rectangle(float(blit_x), float(blit_y),
                               float(blit_w), float(blit_h))
        rl.draw_texture_pro(self._fb_tmp.texture, tmp_src, tmp_dst,
                            rl.Vector2(0, 0), 0.0, rl.WHITE)
        rl.end_texture_mode()

        if shift_y != 0:
            rd = self._data[:, y:y+h, x:x+w]
            rc = self._chars[:, y:y+h, x:x+w]
            rolled_d = np.roll(rd, shift_y, axis=1)
            rolled_c = np.roll(rc, shift_y, axis=1)
            if shift_y > 0:
                rolled_d[:, :shift_y, :] = 0
                rolled_c[:, :shift_y]    = 0
            else:
                rolled_d[:, shift_y:, :] = 0
                rolled_c[:, shift_y:]    = 0
            self._data[:, y:y+h, x:x+w]  = rolled_d
            self._chars[:, y:y+h, x:x+w] = rolled_c

        if shift_x != 0:
            rd = self._data[:, y:y+h, x:x+w]
            rc = self._chars[:, y:y+h, x:x+w]
            rolled_d = np.roll(rd, shift_x, axis=2)
            rolled_c = np.roll(rc, shift_x, axis=2)
            if shift_x > 0:
                rolled_d[:, :, :shift_x] = 0
                rolled_c[:, :, :shift_x] = 0
            else:
                rolled_d[:, :, shift_x:] = 0
                rolled_c[:, :, shift_x:] = 0
            self._data[:, y:y+h, x:x+w]  = rolled_d
            self._chars[:, y:y+h, x:x+w] = rolled_c

    def blit(self, region,
             x=0, y=0, w=None, h=None,
             sx=0, sy=0,
             fx=0.0, fy=0.0, fsx=1.0, fsy=1.0,
             doclear=False):
        cols, rows = self.vis_cells()
        bw  = w if w is not None and w < cols else cols
        bh  = h if h is not None and h < rows else rows
        geo = (fx, fy, fsx, fsy) if (fx or fy or fsx != 1.0 or fsy != 1.0) else None

        dst_rows = self._data.shape[1]
        dst_cols = self._data.shape[2]

        for lyr_idx in range(LYR_COUNT):
            if not region.blit_flags[lyr_idx]:
                continue
            src_d = region._data[lyr_idx]
            src_c = region._chars[lyr_idx]
            dst_d = self._data[lyr_idx]
            dst_c = self._chars[lyr_idx]

            if doclear:
                cx, cy, cw, ch, _, _ = _clip_rect(x, y, bw, bh, dst_cols, dst_rows)
                if cw > 0 and ch > 0:
                    dst_d[cy:cy+ch, cx:cx+cw] = 0
                    dst_c[cy:cy+ch, cx:cx+cw] = 0

            layer_blit(dst_d, src_d, x, y, sx, sy, bw, bh, geo)
            layer_blit(dst_c, src_c, x, y, sx, sy, bw, bh, geo)

            vcols = min(bw, src_d.shape[1] - sx)
            vrows = min(bh, src_d.shape[0] - sy)
            if vcols <= 0 or vrows <= 0:
                continue
            dx, dy, cw2, ch2, _, _ = _clip_rect(x, y, vcols, vrows, dst_cols, dst_rows)
            if cw2 > 0 and ch2 > 0:
                self._dirty.mark_rect(dx, dy, cw2, ch2)

    def layer(self, lyr):
        return self._data[lyr]

    @property
    def under(self): return self._data[LYR_UNDER]
    @property
    def main(self):  return self._data[LYR_MAIN]
    @property
    def over(self):  return self._data[LYR_OVER]

    def set_rendered_layers(self, *flags):
        changed = False
        for i, f in enumerate(flags):
            if i >= LYR_COUNT: break
            v = bool(f)
            if self._layer_visible[i] != v:
                self._layer_visible[i] = v
                changed = True
        if changed:
            self._dirty.mark_full()

    @classmethod
    def from_cell_counts(cls, cols, rows, title="renderer"):
        win_w = int(cols * BASE_CELL_W)
        win_h = int(rows * BASE_CELL_H)
        return cls(win_w=win_w, win_h=win_h, title=title)

    def init(self):
        rl.set_config_flags(rl.FLAG_MSAA_4X_HINT | rl.FLAG_WINDOW_RESIZABLE)
        rl.init_window(self._win_w, self._win_h, self._title)
        rl.set_target_fps(60)
        init_quads_ffi()
        self._sdf.init(float(self._win_w), float(self._win_h))
        self._recalc_cell()
        self._fb     = rl.load_render_texture(self._win_w, self._win_h)
        self._fb_tmp = rl.load_render_texture(self._win_w, self._win_h)
        self._data  = np.zeros((LYR_COUNT, DATABUFFER_ROWS, DATABUFFER_COLS, CH_COUNT, 4),
                               dtype=np.uint8)
        self._chars = np.zeros((LYR_COUNT, DATABUFFER_ROWS, DATABUFFER_COLS),
                               dtype=np.uint32)
        self._dirty.mark_full()

    def _recalc_cell(self):
        cw, ch = _lod_cell_size(self._zoom)
        self._cell_w_f       = cw
        self._cell_h_f       = ch
        self._font_draw_size = DEFAULT_FONT_SIZE * (ch / BASE_CELL_H)

    def _check_resize(self):
        w = rl.get_screen_width()
        h = rl.get_screen_height()
        if w == self._win_w and h == self._win_h:
            return
        self._win_w = w; self._win_h = h
        rl.unload_render_texture(self._fb)
        rl.unload_render_texture(self._fb_tmp)
        self._fb     = rl.load_render_texture(w, h)
        self._fb_tmp = rl.load_render_texture(w, h)
        self._sdf.init(float(w), float(h))
        self._dirty.mark_full()

    def shutdown(self):
        if self._fb:     rl.unload_render_texture(self._fb)
        if self._fb_tmp: rl.unload_render_texture(self._fb_tmp)
        self._sdf.shutdown()
        rl.close_window()

    def vis_cells(self):
        cols = int(self._win_w / self._cell_w_f) + 1
        rows = int(self._win_h / self._cell_h_f) + 1
        return cols, rows

    def cell_size(self):
        return self._cell_w_f, self._cell_h_f

    def mark_dirty(self):
        self._dirty.mark_full()

    def on_mouse_down(self, fn): self._events.on_mouse_down(fn)
    def on_mouse_up(self,   fn): self._events.on_mouse_up(fn)
    def on_file_drop(self,  fn): self._events.on_file_drop(fn)

    def get_mouse_cell_pos(self):
        mp = rl.get_mouse_position()
        return (int(mp.x / self._cell_w_f), int(mp.y / self._cell_h_f))

    def _apply_zoom(self, delta):
        new_zoom = max(ZOOM_MIN, min(ZOOM_MAX, self._zoom + delta * 0.3))
        if abs(new_zoom - self._zoom) < 1e-6: return
        old_cw, _ = _lod_cell_size(self._zoom)
        new_cw, _ = _lod_cell_size(new_zoom)
        if new_cw < float(len(_LOD_SIZES) + 1) and old_cw == new_cw:
            self._zoom = new_zoom
            return
        self._zoom = new_zoom
        self._recalc_cell()
        self._dirty.mark_full()

    def _render_cells_rect(self, px, py, pw, ph, cw_f, ch_f, draw_size, lod_only):
        col0 = int(px / cw_f)
        row0 = int(py / ch_f)
        col1 = int((px + pw + cw_f - 1.0) / cw_f)
        row1 = int((py + ph + ch_f - 1.0) / ch_f)
        vis_cols, vis_rows = self.vis_cells()
        col0 = max(0, col0); row0 = max(0, row0)
        col1 = min(vis_cols + 1, col1); row1 = min(vis_rows + 1, row1)
        if col1 <= col0 or row1 <= row0: return

        layer_data = []
        for i in range(LYR_COUNT):
            if not self._layer_visible[i]:
                continue
            arr_u8  = self._data[i]
            arr_cp  = self._chars[i]
            r0 = max(0, row0); r1 = min(arr_u8.shape[0], row1)
            c0 = max(0, col0); c1 = min(arr_u8.shape[1], col1)
            if r1 <= r0 or c1 <= c0:
                continue
            view_u8 = arr_u8[r0:r1, c0:c1]   # uint8 (rows, cols, CH_COUNT, 4)
            view_cp = arr_cp[r0:r1, c0:c1]   # uint32 (rows, cols)

            ox_px, oy_px, sx_f, sy_f = _decode_geo(view_u8[:, :, CH_GEO, :], cw_f, ch_f)
            rows_idx = np.arange(r1 - r0, dtype=np.float32).reshape(-1, 1)
            cols_idx = np.arange(c1 - c0, dtype=np.float32).reshape(1, -1)
            base_x = (c0 + cols_idx) * cw_f + ox_px
            base_y = (r0 + rows_idx) * ch_f + oy_px
            layer_data.append((view_u8, view_cp, base_x, base_y, sx_f, sy_f))

        for (view_u8, view_cp, base_x, base_y, sx_f, sy_f) in layer_data:
            self._sdf.render_view(view_u8, view_cp, base_x, base_y, sx_f, sy_f,
                                  cw_f, ch_f, draw_size)

    def _render_to_fb(self):
        cw_f      = self._cell_w_f
        ch_f      = self._cell_h_f
        draw_size = self._font_draw_size
        lod_only  = cw_f < LOD_GLYPH_MIN_PX
        vis_cols, vis_rows = self.vis_cells()
        rects = list(self._dirty.consume_pixel_rects(cw_f, ch_f, vis_cols, vis_rows))
        if not rects: return
        rl.begin_texture_mode(self._fb)
        if len(rects) == 1 and rects[0] is None:
            rl.clear_background(rl.WHITE)
            self._render_cells_rect(0, 0,
                                    vis_cols * cw_f, vis_rows * ch_f,
                                    cw_f, ch_f, draw_size, lod_only)
        else:
            for (px, py, pw, ph) in rects:
                ix = int(px); iy = int(py)
                iw = int(pw); ih = int(ph)
                rl.begin_scissor_mode(ix, iy, iw, ih)
                rl.draw_rectangle(ix, iy, iw, ih, rl.WHITE)
                self._render_cells_rect(float(ix), float(iy),
                                        float(iw), float(ih + 3),
                                        cw_f, ch_f, draw_size, lod_only)
                rl.end_scissor_mode()
        rl.end_texture_mode()

    def run(self, update_fn=None):
        while not rl.window_should_close():
            self._check_resize()
            self._events.process(self)
            if update_fn:
                update_fn(self)
            if self._dirty.is_dirty():
                self._render_to_fb()
            rl.begin_drawing()
            rl.clear_background(rl.WHITE)
            src = rl.Rectangle(0, 0,
                               float(self._fb.texture.width),
                               float(-self._fb.texture.height))
            dst = rl.Rectangle(0, 0, float(self._win_w), float(self._win_h))
            rl.draw_texture_pro(self._fb.texture, src, dst,
                                rl.Vector2(0, 0), 0.0, rl.WHITE)
            rl.draw_fps(600, 0)
            rl.end_drawing()
        self.shutdown()
