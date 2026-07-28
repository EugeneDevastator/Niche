# _ni_core/niche_drawbox.py
import numpy as np
from .layer import CH_CHAR, LYR_MAIN, CH_COUNT, LYR_COUNT

BOX_ADD     = 0
BOX_REPLACE = 1
BOX_SUB     = 2

_BOX = {
    (0, 1, 0, 0): '╴', (0, 0, 0, 1): '╶', (1, 0, 0, 0): '╵', (0, 0, 1, 0): '╷',
    (0, 1, 0, 1): '─', (1, 0, 1, 0): '│',
    (0, 1, 1, 0): '┌', (0, 0, 1, 1): '┐', (1, 1, 0, 0): '└', (1, 0, 0, 1): '┘',
    (1, 1, 1, 0): '├', (1, 0, 1, 1): '┤', (0, 1, 1, 1): '┬', (1, 1, 0, 1): '┴',
    (1, 1, 1, 1): '┼',
    (0, 2, 0, 2): '═', (2, 0, 2, 0): '║',
    (0, 2, 2, 0): '╔', (0, 0, 2, 2): '╗', (2, 2, 0, 0): '╚', (2, 0, 0, 2): '╝',
    (2, 2, 2, 0): '╠', (2, 0, 2, 2): '╣', (0, 2, 2, 2): '╦', (2, 2, 0, 2): '╩',
    (2, 2, 2, 2): '╬',
    (0, 2, 1, 0): '╒', (0, 0, 1, 2): '╕', (1, 2, 0, 0): '╘', (1, 0, 0, 2): '╛',
    (0, 1, 2, 0): '╓', (0, 0, 2, 1): '╖', (2, 1, 0, 0): '╙', (2, 0, 0, 1): '╜',
    (1, 2, 1, 2): '╪', (2, 1, 2, 1): '╫',
    (1, 2, 1, 0): '╞', (1, 0, 1, 2): '╡',
    (0, 2, 1, 2): '╤', (1, 2, 0, 2): '╧',
    (2, 1, 2, 0): '╟', (2, 0, 2, 1): '╢',
    (0, 1, 2, 1): '╥', (2, 1, 0, 1): '╨',
}

_CHAR_TO_SIDES = {v: k for k, v in _BOX.items()}

def _sides_of(ch):
    return _CHAR_TO_SIDES.get(ch, None)

def _sides_to_char(sides):
    t, r, b, l = sides
    if t == 0 and r == 0 and b == 0 and l == 0:
        return ' '
    key = tuple(sides)
    ch = _BOX.get(key, None)
    if ch is not None:
        return ch
    nz = lambda a, b_: min(a, b_) if a > 0 and b_ > 0 else max(a, b_)
    h = nz(r, l); v = nz(t, b)
    t2 = v if t > 0 else 0; b2 = v if b > 0 else 0
    r2 = h if r > 0 else 0; l2 = h if l > 0 else 0
    return _BOX.get((t2, r2, b2, l2), None)

def _get_char(da, chars, x, y):
    if x < 0 or y < 0 or x >= da.shape[1] or y >= da.shape[0]:
        return ' '
    code = int(chars[y, x])
    return chr(code) if code > 0 else ' '

def _set_char(da, chars, x, y, ch):
    cp = ord(ch)
    da[y, x, CH_CHAR, 0] = cp & 0xFF
    chars[y, x] = cp

def _merge_char(da, chars, x, y, new_sides, mode):
    cur = _get_char(da, chars, x, y)
    cur_sides = _sides_of(cur)
    cur_sides = list(cur_sides) if cur_sides is not None else [0, 0, 0, 0]
    result = list(cur_sides)
    for i in range(4):
        if new_sides[i] == 0:
            continue
        if mode == BOX_ADD:
            result[i] = max(result[i], new_sides[i])
        elif mode == BOX_SUB:
            if result[i] == new_sides[i]:
                result[i] = 0
    ch = _sides_to_char(result)
    if ch is None:
        return
    _set_char(da, chars, x, y, ch)

def _weight(style):
    return 1 if style == '-' else 2

def _reg_ensure(region, x, y):
    nc = max(region.cols, x + 1)
    nr = max(region.rows, y + 1)
    if nc > region.cols or nr > region.rows:
        new_d = np.zeros((LYR_COUNT, nr, nc, CH_COUNT, 4), dtype=np.uint8)
        new_c = np.zeros((LYR_COUNT, nr, nc), dtype=np.uint32)
        new_d[:, :region.rows, :region.cols] = region._data
        new_c[:, :region.rows, :region.cols] = region._chars
        region._data  = new_d
        region._chars = new_c
        region.cols   = nc
        region.rows   = nr


def drawbox(region, x, y, w, h, style='-', mode=BOX_ADD, lyr=LYR_MAIN):
    if w < 2 or h < 2:
        return

    x2, y2 = x + w - 1, y + h - 1
    _reg_ensure(region, x2, y2)
    da    = region._data[lyr]
    chars = region._chars[lyr]

    if style not in ('-', '='):
        if len(style) < 3:
            return
        corner, hline, vline = style[0], style[1], style[2]
        _set_char(da, chars, x,  y,  corner)
        _set_char(da, chars, x2, y,  corner)
        _set_char(da, chars, x,  y2, corner)
        _set_char(da, chars, x2, y2, corner)
        for cx in range(x+1, x2):
            _set_char(da, chars, cx, y,  hline)
            _set_char(da, chars, cx, y2, hline)
        for cy in range(y+1, y2):
            _set_char(da, chars, x,  cy, vline)
            _set_char(da, chars, x2, cy, vline)
        return

    w_ = _weight(style)

    if mode == BOX_REPLACE:
        _set_char(da, chars, x,  y,  _sides_to_char([0,  w_, w_, 0 ]))
        _set_char(da, chars, x2, y,  _sides_to_char([0,  0,  w_, w_]))
        _set_char(da, chars, x,  y2, _sides_to_char([w_, w_, 0,  0 ]))
        _set_char(da, chars, x2, y2, _sides_to_char([w_, 0,  0,  w_]))
        h_ = _sides_to_char([0, w_, 0, w_])
        v_ = _sides_to_char([w_, 0, w_, 0])
        for cx in range(x+1, x2):
            _set_char(da, chars, cx, y,  h_)
            _set_char(da, chars, cx, y2, h_)
        for cy in range(y+1, y2):
            _set_char(da, chars, x,  cy, v_)
            _set_char(da, chars, x2, cy, v_)
        return

    _merge_char(da, chars, x,  y,  [0,  w_, w_, 0 ], mode)
    _merge_char(da, chars, x2, y,  [0,  0,  w_, w_], mode)
    _merge_char(da, chars, x,  y2, [w_, w_, 0,  0 ], mode)
    _merge_char(da, chars, x2, y2, [w_, 0,  0,  w_], mode)
    for cx in range(x+1, x2):
        _merge_char(da, chars, cx, y,  [0, w_, 0, w_], mode)
        _merge_char(da, chars, cx, y2, [0, w_, 0, w_], mode)
    for cy in range(y+1, y2):
        _merge_char(da, chars, x,  cy, [w_, 0, w_, 0], mode)
        _merge_char(da, chars, x2, cy, [w_, 0, w_, 0], mode)


class BoxPen:
    def __init__(self, region, style='-', mode=BOX_ADD, lyr=LYR_MAIN):
        self._region = region
        self._style  = style
        self._mode   = mode
        self._lyr    = lyr
        self._x = 0
        self._y = 0

    def style(self, s):   self._style = s; return self
    def mode(self, m):    self._mode  = m; return self
    def move(self, x, y): self._x, self._y = x, y; return self

    def box(self, w, h):
        drawbox(self._region, self._x, self._y, w, h, self._style, self._mode, self._lyr)
        return self

    def box_to(self, x2, y2):
        x = min(self._x, x2); y = min(self._y, y2)
        w = abs(x2 - self._x) + 1; h = abs(y2 - self._y) + 1
        drawbox(self._region, x, y, w, h, self._style, self._mode, self._lyr)
        return self

    def line_to(self, x2, y2):
        x1, y1 = self._x, self._y
        w_ = _weight(self._style) if self._style in ('-', '=') else 1
        _reg_ensure(self._region, max(x1, x2), max(y1, y2))
        da    = self._region._data[self._lyr]
        chars = self._region._chars[self._lyr]
        if x1 == x2:
            y_lo, y_hi = (y1, y2) if y1 <= y2 else (y2, y1)
            for y in range(y_lo, y_hi + 1):
                _merge_char(da, chars, x1, y, [w_, 0, w_, 0], self._mode)
        else:
            x_lo, x_hi = (x1, x2) if x1 <= x2 else (x2, x1)
            for x in range(x_lo, x_hi + 1):
                _merge_char(da, chars, x, y1, [0, w_, 0, w_], self._mode)
        self._x, self._y = x2, y2
        return self
