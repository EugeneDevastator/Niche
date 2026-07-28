# _ni_core/layer.py
import numpy as np

CH_CHAR      = 0
CH_SEMANTICS = 1
CH_VISSIZE   = 2
CH_FG        = 3
CH_BG        = 4
CH_STYLE     = 5
CH_FLEX      = 6
CH_GEO       = 7
CH_COUNT     = 8

LYR_UNDER = 0
LYR_MAIN  = 1
LYR_OVER  = 2
LYR_COUNT = 3


def make_layer(rows, cols, dtype=np.uint8):
    return np.zeros((rows, cols, CH_COUNT, 4), dtype=dtype)


def _clip_rect(x, y, w, h, max_cols, max_rows):
    x0 = max(0, x);  y0 = max(0, y)
    x1 = min(max_cols, x + w)
    y1 = min(max_rows, y + h)
    ox = x0 - x;  oy = y0 - y
    return x0, y0, max(0, x1 - x0), max(0, y1 - y0), ox, oy


def layer_blit(dst, src, dx, dy, sx, sy, w, h, geo):
    dst_rows, dst_cols = dst.shape[0], dst.shape[1]
    src_rows, src_cols = src.shape[0], src.shape[1]

    # clip source
    sx0 = max(0, sx);  sy0 = max(0, sy)
    sx1 = min(src_cols, sx + w)
    sy1 = min(src_rows, sy + h)
    cw  = sx1 - sx0;  ch = sy1 - sy0
    if cw <= 0 or ch <= 0:
        return

    # offset into dst
    ddx = dx + (sx0 - sx)
    ddy = dy + (sy0 - sy)

    # clip dest
    dx0 = max(0, ddx);  dy0 = max(0, ddy)
    dx1 = min(dst_cols, ddx + cw)
    dy1 = min(dst_rows, ddy + ch)
    cw2 = dx1 - dx0;  ch2 = dy1 - dy0
    if cw2 <= 0 or ch2 <= 0:
        return

    # adjust source for dest clip
    ssx = sx0 + (dx0 - ddx)
    ssy = sy0 + (dy0 - ddy)

    dst[dy0:dy0+ch2, dx0:dx0+cw2] = src[ssy:ssy+ch2, ssx:ssx+cw2]
