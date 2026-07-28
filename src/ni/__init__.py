# ni.py
import numpy as np
from typing import Optional

from _ni_core.layer import (
    CH_CHAR, CH_SEMANTICS, CH_VISSIZE, CH_FG, CH_BG, CH_STYLE, CH_FLEX, CH_GEO, CH_COUNT,
    LYR_UNDER, LYR_MAIN, LYR_OVER, LYR_COUNT,
    _clip_rect, layer_blit,
)
from _ni_core.niche_render import (
    Renderer,
    DEFAULT_FONT_SIZE, BASE_CELL_W, BASE_CELL_H,
    ZOOM_MIN, ZOOM_MAX, DATABUFFER_COLS, DATABUFFER_ROWS,
)
from _ni_core.niche_drawbox import drawbox as _drawbox, BOX_ADD, BOX_REPLACE, BOX_SUB
from _ni_core.niche_input import EventBus

_rend: Optional[Renderer] = None
viewregion: Optional['Region'] = None

def init(win_w: int = 1280, win_h: int = 720, title: str = "ni"):
    global _rend, viewregion
    _rend = Renderer(win_w, win_h, title)
    _rend.init()
    vr = Region.__new__(Region)
    vr.rid        = -1
    vr.cols       = DATABUFFER_COLS
    vr.rows       = DATABUFFER_ROWS
    vr.blit_flags = [True] * LYR_COUNT
    vr._data      = _rend._data
    vr._chars     = _rend._chars
    vr._cursors   = {}
    viewregion = vr

def run(update_fn=None):
    assert _rend is not None, "call ni.init() first"
    _rend.run(update_fn)

def mark_dirty():
    assert _rend is not None
    _rend.mark_dirty()

def vis_cells():
    assert _rend is not None
    return _rend.vis_cells()

def cell_size():
    assert _rend is not None
    return _rend.cell_size()

def get_mouse_cell_pos():
    assert _rend is not None
    return _rend.get_mouse_cell_pos()

def on_mouse_down(fn): _rend.on_mouse_down(fn)
def on_mouse_up(fn):   _rend.on_mouse_up(fn)
def on_file_drop(fn):  _rend.on_file_drop(fn)


# --- Encoding helpers ---

def _enc_geo_offset(v):
    # float -4..4 → uint8: 128 + v*32
    return int(max(0, min(255, round(128.0 + v * 32.0))))

def _enc_geo_scale(v):
    # float 0..4 → uint8: v*64; 0 stored as 0 means "default 1.0" at decode
    return int(max(0, min(255, round(v * 64.0))))

def _enc_bold(v):
    # 0..2 → uint8: v*127 (clamped)
    return int(max(0, min(255, round(v * 127.0))))

def _enc_skew(v):
    # -1..1 → uint8: 128 + v*127
    return int(max(0, min(255, round(128.0 + v * 127.0))))


class CellStyle:
    __slots__ = ('fg', 'bg', 'char', 'bold_f', 'skew_f', 'offsetscale', 'get_char_from_main')
    def __init__(self, fg=None, bg=None, char=None,
                 bold_f=None, skew_f=None, offsetscale=None,
                 get_char_from_main=False):
        self.fg               = fg
        self.bg               = bg
        self.char             = char
        self.bold_f           = bold_f
        self.skew_f           = skew_f
        self.offsetscale      = offsetscale
        self.get_char_from_main = get_char_from_main


class NiStyle:
    __slots__ = ('under', 'main', 'over')
    def __init__(self, under=None, main=None, over=None):
        self.under = under if under is not None else CellStyle()
        self.main  = main  if main  is not None else CellStyle()
        self.over  = over  if over  is not None else CellStyle()

Style = NiStyle


class Region:
    __slots__ = ('rid', 'cols', 'rows', 'blit_flags', '_data', '_chars', '_cursors')
    def __init__(self, rid: int, cols: int, rows: int):
        self.rid        = rid
        self.cols       = cols
        self.rows       = rows
        self.blit_flags = [True] * LYR_COUNT
        self._data      = np.zeros((LYR_COUNT, rows, cols, CH_COUNT, 4), dtype=np.uint8)
        self._chars     = np.zeros((LYR_COUNT, rows, cols), dtype=np.uint32)
        self._cursors   = {}


TAB_SIZE = 4

def _reg_ensure(reg: Region, x: int, y: int):
    if reg is viewregion:
        return
    nc = max(reg.cols, x + 1)
    nr = max(reg.rows, y + 1)
    if nc > reg.cols or nr > reg.rows:
        new_d = np.zeros((LYR_COUNT, nr, nc, CH_COUNT, 4), dtype=np.uint8)
        new_c = np.zeros((LYR_COUNT, nr, nc), dtype=np.uint32)
        new_d[:, :reg.rows, :reg.cols] = reg._data
        new_c[:, :reg.rows, :reg.cols] = reg._chars
        reg._data  = new_d
        reg._chars = new_c
        reg.cols   = nc
        reg.rows   = nr

def _lyr(reg: Region, lyr: int) -> np.ndarray:
    return reg._data[lyr]

def _lyr_chars(reg: Region, lyr: int) -> np.ndarray:
    return reg._chars[lyr]


def _write_cs_to_view(data_view: np.ndarray, chars_view: np.ndarray,
                      cs: CellStyle, main_chars=None):
    """
    data_view:  shape (h, w, CH_COUNT, 4) uint8
    chars_view: shape (h, w) uint32
    """
    if cs.fg is not None:
        data_view[:, :, CH_FG, :] = np.array(cs.fg, dtype=np.uint8)
    if cs.bg is not None:
        data_view[:, :, CH_BG, :] = np.array(cs.bg, dtype=np.uint8)
    if cs.bold_f is not None:
        data_view[:, :, CH_STYLE, 0] = _enc_bold(cs.bold_f)
    if cs.skew_f is not None:
        data_view[:, :, CH_STYLE, 1] = _enc_skew(cs.skew_f)
    if cs.offsetscale is not None:
        os_ = cs.offsetscale
        data_view[:, :, CH_GEO, 0] = _enc_geo_offset(os_[0])
        data_view[:, :, CH_GEO, 1] = _enc_geo_offset(os_[1])
        data_view[:, :, CH_GEO, 2] = _enc_geo_scale(os_[2])
        data_view[:, :, CH_GEO, 3] = _enc_geo_scale(os_[3])
    if cs.char is not None:
        cp = ord(cs.char[0])
        chars_view[:, :] = cp
        data_view[:, :, CH_CHAR, 0] = min(cp, 255)
    if cs.get_char_from_main and main_chars is not None:
        chars_view[:, :] = main_chars
        data_view[:, :, CH_CHAR, 0] = np.clip(main_chars, 0, 255).astype(np.uint8)


def region(rid: int, cols: int, rows: int) -> Region:
    return Region(rid, cols, rows)

def cellstyle(fg=None, bg=None, char=None,
              bold_f=None, skew_f=None, offsetscale=None,
              get_char_from_main=False) -> CellStyle:
    return CellStyle(fg=fg, bg=bg, char=char,
                     bold_f=bold_f, skew_f=skew_f,
                     offsetscale=offsetscale,
                     get_char_from_main=get_char_from_main)

def nistyle(under=None, main=None, over=None) -> NiStyle:
    return NiStyle(under=under, main=main, over=over)


def setpos(reg: Region, x: int, y: int, key=0):
    reg._cursors[key] = (x, y)

def getpos(reg: Region, key=0) -> tuple:
    return reg._cursors.get(key, (0, 0))


def writeline(reg: Region, text: str, st: NiStyle = None, lyr: int = LYR_MAIN, key=0):
    x, y = reg._cursors.get(key, (0, 0))
    _write_text(reg, x, y, text, st, lyr)
    reg._cursors[key] = (x, y + 1)

def write(reg: Region, text: str, st: NiStyle = None, lyr: int = LYR_MAIN, key=0):
    x, y = reg._cursors.get(key, (0, 0))
    _write_text(reg, x, y, text, st, lyr)
    reg._cursors[key] = (x + len(text), y)

def _write_text(reg: Region, x: int, y: int, text: str, st: NiStyle, lyr: int):
    ox = x
    for ch in text:
        if ch == '\n':
            x = ox; y += 1; continue
        if ch == '\t':
            x = ox + ((x - ox + TAB_SIZE) // TAB_SIZE) * TAB_SIZE
            continue
        _reg_ensure(reg, x, y)
        cp = ord(ch)
        reg._chars[lyr, y, x] = cp
        reg._data[lyr, y, x, CH_CHAR, 0] = min(cp, 255)
        # only apply full NiStyle when writing to main layer
        if st is not None and lyr == LYR_MAIN:
            _apply_style_cell(reg, x, y, st)
        x += 1

def _apply_style_cell(reg: Region, x: int, y: int, st: NiStyle):
    lyr_indices = (LYR_UNDER, LYR_MAIN, LYR_OVER)
    main_chars = None
    for lyr_i, cs in zip(lyr_indices, (st.under, st.main, st.over)):
        if cs is None:
            continue
        if cs.get_char_from_main and main_chars is None:
            main_chars = reg._chars[LYR_MAIN, y:y+1, x:x+1].copy()
        _reg_ensure(reg, x, y)
        dv = reg._data[lyr_i, y:y+1, x:x+1]
        cv = reg._chars[lyr_i, y:y+1, x:x+1]
        _write_cs_to_view(dv, cv, cs, main_chars)

def fillstyle(reg: Region, x: int, y: int, w: int, h: int, st: NiStyle):
    _reg_ensure(reg, x + w - 1, y + h - 1)
    main_chars = reg._chars[LYR_MAIN, y:y+h, x:x+w].copy()
    lyr_indices = (LYR_UNDER, LYR_MAIN, LYR_OVER)
    for lyr_i, cs in zip(lyr_indices, (st.under, st.main, st.over)):
        if cs is None:
            continue
        dv = reg._data[lyr_i, y:y+h, x:x+w]
        cv = reg._chars[lyr_i, y:y+h, x:x+w]
        mc = main_chars if cs.get_char_from_main else None
        _write_cs_to_view(dv, cv, cs, mc)

def fillchar(reg: Region, x: int, y: int, w: int, h: int,
             char: str, lyr: int = LYR_MAIN):
    _reg_ensure(reg, x + w - 1, y + h - 1)
    cp = ord(char[0])
    reg._chars[lyr, y:y+h, x:x+w] = cp
    reg._data[lyr, y:y+h, x:x+w, CH_CHAR, 0] = min(cp, 255)

def clear(reg: Region, x: int = 0, y: int = 0,
          w: int = None, h: int = None, lyr: int = LYR_MAIN):
    x2 = min(x + (w if w is not None else reg.cols), reg.cols)
    y2 = min(y + (h if h is not None else reg.rows), reg.rows)
    if x2 > x and y2 > y:
        reg._data[lyr, y:y2, x:x2] = 0
        reg._chars[lyr, y:y2, x:x2] = 0

def clearall(reg: Region, x: int = 0, y: int = 0,
             w: int = None, h: int = None):
    x2 = min(x + (w if w is not None else reg.cols), reg.cols)
    y2 = min(y + (h if h is not None else reg.rows), reg.rows)
    if x2 > x and y2 > y:
        reg._data[:, y:y2, x:x2] = 0
        reg._chars[:, y:y2, x:x2] = 0


def box(reg: Region, x: int, y: int, w: int, h: int,
        stroke_char='-', mode: int = BOX_ADD, lyr: int = LYR_MAIN,
        st_stroke: NiStyle = None, st_fill: NiStyle = None):
    _drawbox(reg, x, y, w, h, stroke_char, mode, lyr)
    if st_stroke is not None:
        fillstyle(reg, x,     y,       w,   1,   st_stroke)
        fillstyle(reg, x,     y+h-1,   w,   1,   st_stroke)
        fillstyle(reg, x,     y+1,     1,   h-2, st_stroke)
        fillstyle(reg, x+w-1, y+1,     1,   h-2, st_stroke)
    if st_fill is not None and w > 2 and h > 2:
        fillstyle(reg, x+1, y+1, w-2, h-2, st_fill)


def copy(reg: Region, x: int, y: int, w: int, h: int):
    cx, cy, cw, ch, _, _ = _clip_rect(x, y, w, h, reg.cols, reg.rows)
    if cw <= 0 or ch <= 0:
        return None, None
    return (reg._data[:, cy:cy+ch, cx:cx+cw].copy(),
            reg._chars[:, cy:cy+ch, cx:cx+cw].copy())

def paste(reg: Region, arr, x: int, y: int):
    if arr is None:
        return
    data_arr, chars_arr = arr
    if data_arr is None:
        return
    ah, aw = data_arr.shape[1], data_arr.shape[2]
    _reg_ensure(reg, x + aw - 1, y + ah - 1)
    reg._data[:, y:y+ah, x:x+aw]  = data_arr
    reg._chars[:, y:y+ah, x:x+aw] = chars_arr

def copy_layer(reg: Region, x: int, y: int, w: int, h: int,
               lyr: int = LYR_MAIN):
    cx, cy, cw, ch, _, _ = _clip_rect(x, y, w, h, reg.cols, reg.rows)
    if cw <= 0 or ch <= 0:
        return None, None
    return (reg._data[lyr, cy:cy+ch, cx:cx+cw].copy(),
            reg._chars[lyr, cy:cy+ch, cx:cx+cw].copy())

def paste_layer(reg: Region, arr, x: int, y: int,
                lyr: int = LYR_MAIN):
    if arr is None:
        return
    data_arr, chars_arr = arr
    if data_arr is None:
        return
    ah, aw = data_arr.shape[0], data_arr.shape[1]
    _reg_ensure(reg, x + aw - 1, y + ah - 1)
    reg._data[lyr, y:y+ah, x:x+aw]  = data_arr
    reg._chars[lyr, y:y+ah, x:x+aw] = chars_arr


def blit(reg_to: Region, reg_src: Region,
         x: int = 0, y: int = 0,
         w: int = None, h: int = None,
         sxfrom: int = 0, syfrom: int = 0):
    bw = w if w is not None else reg_src.cols
    bh = h if h is not None else reg_src.rows
    _reg_ensure(reg_to, x + bw - 1, y + bh - 1)
    for lyr_idx in range(LYR_COUNT):
        if not reg_src.blit_flags[lyr_idx]:
            continue
        layer_blit(reg_to._data[lyr_idx], reg_src._data[lyr_idx],
                   x, y, sxfrom, syfrom, bw, bh, None)
        layer_blit(reg_to._chars[lyr_idx], reg_src._chars[lyr_idx],
                   x, y, sxfrom, syfrom, bw, bh, None)

def blitlayer(reg_to: Region, reg_src: Region,
              x: int = 0, y: int = 0,
              w: int = None, h: int = None,
              sxfrom: int = 0, syfrom: int = 0,
              lyr: int = LYR_MAIN):
    bw = w if w is not None else reg_src.cols
    bh = h if h is not None else reg_src.rows
    _reg_ensure(reg_to, x + bw - 1, y + bh - 1)
    layer_blit(reg_to._data[lyr], reg_src._data[lyr],
               x, y, sxfrom, syfrom, bw, bh, None)
    layer_blit(reg_to._chars[lyr], reg_src._chars[lyr],
               x, y, sxfrom, syfrom, bw, bh, None)

def blitmain(reg_src: Region,
             x: int = 0, y: int = 0,
             w: int = None, h: int = None,
             sxfrom: int = 0, syfrom: int = 0,
             doclear: bool = False):
    assert _rend is not None, "call ni.init() first"
    _rend.blit(reg_src, x=x, y=y, w=w, h=h, sx=sxfrom, sy=syfrom, doclear=doclear)


def shift(x, y, w, h, shift_x, shift_y,
          preserve_bound=True, clear_freed=True):
    assert _rend is not None, "call ni.init() first"
    _rend.shift_texture(x, y, w, h, shift_x, shift_y, preserve_bound, clear_freed)
