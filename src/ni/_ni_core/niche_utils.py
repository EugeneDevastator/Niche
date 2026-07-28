# ren_utils.py
from .niche_render import Renderer, CH_CHAR, CH_FG, CH_BG, LYR_MAIN


def write_text(rend: Renderer, rid: int, x: int, y: int, text: str,
               fg: tuple = (30, 30, 30, 255), bg: tuple = (0, 0, 0, 0), layer: int = LYR_MAIN):
    rend.write_at(rid, x, y, CH_CHAR, text)
    rend.write_at(rid, x, y, CH_FG,  bytes(fg) * len(text))
    rend.write_at(rid, x, y, CH_BG,  bytes(bg) * len(text))


def blit(rend: Renderer, rid: int,
         x: int = 0, y: int = 0,
         w: int = None, h: int = None,
         sx: int = 0, sy: int = 0,
         doclear: bool = False):
    cols, rows = rend.vis_cells()
    x2 = x + (w if w is not None else cols)
    y2 = y + (h if h is not None else rows)
    rend.draw_region(rid, x, y, x2, y2, sx, sy, 0.0, 0.0, doclear)


def clear_cells(rend: Renderer, rid: int, x: int, y: int, count: int):
    r = rend.get_region(rid)
    if r is None:
        return
    for i in range(count):
        c = r.cell(x + i, y)
        if c:
            c.clear()
    rend._fb_dirty = True