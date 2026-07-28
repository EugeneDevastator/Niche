# nidemo_scroll.py
import time
import numpy as np
import pyray as rl

import ni

WIN_W = 1920
WIN_H = 1200

TOTAL_LINES  = 1200
SCROLL_SPEED = 3
MANUAL_STEP  = 1
WHEEL_STEP   = 3

CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%^&* "

rng = np.random.default_rng(42)

_content_region = None
_hud_region     = None
_scroll_y       = 0
_auto_scroll    = True
_last_update_ms = 0.0
_space_prev     = False
_rendered_top   = -1


def _build_content(cols, rows):
    global _content_region
    content_rows = TOTAL_LINES + rows

    r = ni.Region(0, cols, content_rows)
    char_pool = np.array([ord(c) for c in CHARS], dtype=np.uint32)

    for y in range(TOTAL_LINES):
        prefix = f"line {y:04d} | "
        px = min(len(prefix), cols)
        ni.setpos(r, 0, y)
        ni.write(r, prefix[:px])
        rand_len = cols - px
        if rand_len > 0:
            idx = rng.integers(0, len(char_pool), size=rand_len)
            cps = char_pool[idx]
            r._chars[ni.LYR_MAIN, y, px:cols] = cps
            r._data[ni.LYR_MAIN, y, px:cols, ni.CH_CHAR, 0] = np.clip(cps, 0, 255).astype(np.uint8)

    da = r._data[ni.LYR_MAIN]
    da[:TOTAL_LINES, :cols, ni.CH_FG, 0] = rng.integers(20,  200, (TOTAL_LINES, cols), dtype=np.uint8)
    da[:TOTAL_LINES, :cols, ni.CH_FG, 1] = rng.integers(20,  200, (TOTAL_LINES, cols), dtype=np.uint8)
    da[:TOTAL_LINES, :cols, ni.CH_FG, 2] = rng.integers(20,  200, (TOTAL_LINES, cols), dtype=np.uint8)
    da[:TOTAL_LINES, :cols, ni.CH_FG, 3] = 255

    da[:TOTAL_LINES, :cols, ni.CH_BG, 0] = rng.integers(120, 200, (TOTAL_LINES, cols), dtype=np.uint8)
    da[:TOTAL_LINES, :cols, ni.CH_BG, 1] = rng.integers(120, 200, (TOTAL_LINES, cols), dtype=np.uint8)
    da[:TOTAL_LINES, :cols, ni.CH_BG, 2] = rng.integers(120, 200, (TOTAL_LINES, cols), dtype=np.uint8)
    da[:TOTAL_LINES, :cols, ni.CH_BG, 3] = rng.integers(0,   200, (TOTAL_LINES, cols), dtype=np.uint8)

    da[:TOTAL_LINES, :cols, ni.CH_GEO, 2] = 64
    da[:TOTAL_LINES, :cols, ni.CH_GEO, 3] = 64

    _content_region = r


def _build_hud(cols):
    global _hud_region
    _hud_region = ni.Region(1, cols, 1)


def _write_hud(update_ms: float, scroll: int, fps: int, cols: int):
    mode  = "AUTO" if _auto_scroll else "MANUAL"
    label = (f"[SPACE=toggle] [UP/DN/WHEEL=scroll] mode:{mode}  scroll:{scroll:4d}  "
             f"upd:{update_ms:5.1f}ms  fps:{fps}")

    ni.clear(_hud_region)
    ni.setpos(_hud_region, 0, 0)
    ni.write(_hud_region, label[:cols],
             ni.NiStyle(main=ni.CellStyle(fg=[200, 40, 40, 255])))

    n = min(len(label), cols)
    _hud_region._data[ni.LYR_MAIN, 0, :n, ni.CH_GEO, 2] = 64
    _hud_region._data[ni.LYR_MAIN, 0, :n, ni.CH_GEO, 3] = 64


def _manual_delta():
    """Returns signed scroll delta from keys + wheel when in manual mode."""
    delta = 0
    if rl.is_key_pressed(rl.KEY_DOWN) or rl.is_key_down(rl.KEY_DOWN):
        delta += MANUAL_STEP
    if rl.is_key_pressed(rl.KEY_UP) or rl.is_key_down(rl.KEY_UP):
        delta -= MANUAL_STEP
    wheel = rl.get_mouse_wheel_move()
    if wheel != 0:
        delta -= int(wheel) * WHEEL_STEP  # wheel up = negative = scroll up
    return delta


def update(_rend=None):
    global _scroll_y, _last_update_ms, _auto_scroll, _space_prev, _rendered_top

    vis_cols, vis_rows = ni.vis_cells()
    blit_rows = max(1, vis_rows - 1)

    space_now = rl.is_key_down(rl.KEY_SPACE)
    if space_now and not _space_prev:
        _auto_scroll = not _auto_scroll
    _space_prev = space_now

    t0 = time.perf_counter()

    if _auto_scroll:
        new_scroll = (_scroll_y + SCROLL_SPEED) % TOTAL_LINES
    else:
        d = _manual_delta()
        new_scroll = (_scroll_y + d) % TOTAL_LINES

    delta = (new_scroll - _scroll_y) % TOTAL_LINES

    if _rendered_top < 0 or (delta == 0 and _rendered_top != _scroll_y):
        ni.blitmain(_content_region, x=0, y=1,
                    sxfrom=0, syfrom=new_scroll, doclear=True)
        _rendered_top = new_scroll
    elif delta > 0:
        ni.shift(0, 1, vis_cols, blit_rows, 0, -delta,
                 preserve_bound=True, clear_freed=True)

        new_line_src_y = (new_scroll + blit_rows - delta) % TOTAL_LINES
        lines_before_wrap = TOTAL_LINES - new_line_src_y
        if lines_before_wrap >= delta:
            ni.blitmain(_content_region,
                        x=0, y=1 + blit_rows - delta,
                        w=vis_cols, h=delta,
                        sxfrom=0, syfrom=new_line_src_y, doclear=True)
        else:
            ni.blitmain(_content_region,
                        x=0, y=1 + blit_rows - delta,
                        w=vis_cols, h=lines_before_wrap,
                        sxfrom=0, syfrom=new_line_src_y, doclear=True)
            ni.blitmain(_content_region,
                        x=0, y=1 + blit_rows - delta + lines_before_wrap,
                        w=vis_cols, h=delta - lines_before_wrap,
                        sxfrom=0, syfrom=0, doclear=True)

        _rendered_top = new_scroll

    _scroll_y = new_scroll
    _last_update_ms = (time.perf_counter() - t0) * 1000.0

    _write_hud(_last_update_ms, _scroll_y, rl.get_fps(), vis_cols)
    ni.blitmain(_hud_region, x=0, y=0, w=vis_cols, h=1,
                sxfrom=0, syfrom=0, doclear=True)

    ni.mark_dirty()


def main():
    ni.init(WIN_W, WIN_H, "scroll stress")
    ni._rend.set_rendered_layers(0, 1, 0)

    vis_cols, vis_rows = ni.vis_cells()
    _build_content(10000, vis_rows)
    _build_hud(vis_cols)

    ni.run(update)


if __name__ == "__main__":
    main()
