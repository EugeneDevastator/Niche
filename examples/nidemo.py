# nidemo.py
import ni
import random
import math
import pyray as rl

TEXT = "Hello Shadow World"
N    = len(TEXT)

SHADOW_STYLE = ni.NiStyle(
    under=ni.CellStyle(
        fg=[120, 120, 120, 160],
        bg=[160, 160, 160, 10],
        offsetscale=[0.18, 0.1, 1.0, 1.0],
        get_char_from_main=True,
    ),
    main=ni.CellStyle(
        fg=[20, 20, 20, 255],
        bg=[200, 220, 255, 0],
    ),
)

OVERRIDE_STYLE = ni.NiStyle(
    main=ni.CellStyle(fg=[255, 30, 30, 255]),
    over=ni.CellStyle(bg=[255, 140, 0, 150]),
    under=ni.CellStyle(char='.', fg=[0, 0, 0, 155]),
)

def setup_part1(y_offset: int):
    r = ni.Region(0, N, 1)
    st = ni.NiStyle(
        main=ni.CellStyle(fg=[20, 20, 20, 255], bg=[200, 220, 255, 110]),
        under=ni.CellStyle(fg=[120, 120, 120, 160], bg=[160, 160, 160, 110],
                           offsetscale=[0.18, 0.1, 1.0, 1.0], get_char_from_main=True),
    ) # here there should be no SKEW! but text is skewed. offset moves it several CELLS instead of being relative to cell size and move it slightly.
    ni.setpos(r, 0, 0)
    ni.write(r, TEXT, st, ni.LYR_MAIN)
    ni.setpos(r, 0, 0)
    ni.write(r, TEXT, st, ni.LYR_UNDER)
    ni.blitmain(r, x=5, y=y_offset, w=N, h=1)


def setup_part2(y_offset: int):
    r = ni.Region(1, N, 1)
    ni.setpos(r, 0, 0)
    ni.write(r, TEXT, SHADOW_STYLE)
    ni.blitmain(r, x=5, y=y_offset, w=N, h=1)
    ni.blitmain(r, x=6, y=1 + y_offset, w=N, h=1)


def setup_part3(y_offset: int):
    BOX_W = 24
    BOX_H = 8
    r = ni.Region(2, BOX_W, BOX_H)
    ni.box(r, 0, 0, BOX_W, BOX_H,     '-', ni.BOX_ADD)
    ni.box(r, 0, 2, BOX_W - 8, BOX_H - 4, '=', ni.BOX_ADD)
    ni.setpos(r, 6, 2)
    ni.write(r, "Im a box")
    st = ni.NiStyle(main=ni.CellStyle(fg=[30, 160, 140, 255], bg=[240, 248, 255, 125]))
    ni.fillstyle(r, 0, 0, BOX_W, BOX_H, st)
    ni.blitmain(r, x=5, y=y_offset, w=BOX_W, h=BOX_H)


def setup_part4(y_offset: int):
    ni.fillstyle(ni.viewregion, 12, y_offset, 10, 8, OVERRIDE_STYLE)
    ni.mark_dirty()


def setup_part5_typer(y_offset: int):
    W = 40
    H = 8
    r = ni.Region(5, W, H)
    ni.setpos(r, 0, 0)
    ni.writeline(r, "Typer plain text",
                 ni.NiStyle(main=ni.CellStyle(fg=[30, 30, 30, 255])))
    ni.writeline(r, "Typer bold red",
                 ni.NiStyle(main=ni.CellStyle(fg=[200, 40, 40, 255], bold_f=1.4)))
    ni.writeline(r, "Typer with bg",
                 ni.NiStyle(main=ni.CellStyle(fg=[220, 20, 20, 255], bg=[210, 230, 255, 120])))
    ni.writeline(r, "Typer shadow",
                 ni.NiStyle(
                     main=ni.CellStyle(fg=[20, 20, 20, 255]),
                     under=ni.CellStyle(fg=[160, 160, 160, 140],
                                        offsetscale=[0.15, 0.08, 1.0, 1.0],
                                        get_char_from_main=True),
                 ))
    ni.writeline(r, "Typer skew right",
                 ni.NiStyle(main=ni.CellStyle(fg=[60, 120, 200, 255], skew_f=0.35)))
    ni.writeline(r, "Typer skew left",
                 ni.NiStyle(main=ni.CellStyle(fg=[180, 80, 20, 255], bg=[60, 60, 255, 64], skew_f=-0.35)))
    ni.writeline(r, "col1\tcol2\tcol3",
                 ni.NiStyle(main=ni.CellStyle(fg=[80, 160, 80, 255])))
    ni.writeline(r, "\tindented\tsecond tab",
                 ni.NiStyle(main=ni.CellStyle(fg=[40, 100, 40, 255])))
    ni.blitmain(r, x=35, y=4, w=W, h=H)


def setup_part6_scaleoffset(y_offset: int):
    r = ni.Region(6, 30, 4)
    ni.setpos(r, 0, 0)
    ni.writeline(r, "Normal",
                 ni.NiStyle(main=ni.CellStyle(fg=[30, 30, 30, 255])))
    ni.writeline(r, "Scale1.4 ShiftR",
                 ni.NiStyle(main=ni.CellStyle(
                     fg=[20, 100, 200, 255],
                     offsetscale=[0.2, 0.0, 1.4, 1.4],
                 )))
    ni.writeline(r, "Scale0.6 ShiftD",
                 ni.NiStyle(main=ni.CellStyle(
                     fg=[180, 40, 40, 255],
                     offsetscale=[0.0, 0.3, 0.6, 0.6],
                 )))
    ni.writeline(r, "Scale0.8 ShiftL",
                 ni.NiStyle(main=ni.CellStyle(
                     fg=[40, 160, 80, 255],
                     offsetscale=[-0.2, 0.0, 0.8, 0.8],
                 )))
    ni.blitmain(r, x=18, y=y_offset, w=r.cols, h=r.rows)


_SUP_X = 15
_SUP_Y = 16

def setup_part7_superscript():
    r = ni.Region(7, 3, 1)
    ni.setpos(r, 0, 0)
    ni.write(r, "X",
             ni.NiStyle(main=ni.CellStyle(fg=[20, 20, 200, 255])),
             ni.LYR_MAIN)
    ni.setpos(r, 1, 0)
    ni.write(r, "2",
             ni.NiStyle(
                 main=ni.CellStyle(
                     fg=[20, 160, 20, 255],
                     bg=[0, 200, 80, 160],
                     offsetscale=[-0.05, -0.3, 0.7, 0.7],
                 )
             ),
             ni.LYR_MAIN)
    ni.blitmain(r, x=_SUP_X, y=_SUP_Y, w=3, h=1)


_HOVER_TEXT = "HOVER ME"
_HOVER_LEN  = len(_HOVER_TEXT)
_HOVER_X    = 31
_HOVER_Y    = 18
_FG_NORMAL  = [30,  30,  30,  255]
_FG_HOVER   = [255, 60,  0,   255]
_BG_NORMAL  = [80,  80,  200, 120]
_BG_HOVER   = [255, 200, 0,   180]
_hover_state = False
_char_styles = []

def _gen_char_styles():
    global _char_styles
    _char_styles = []
    for i in range(_HOVER_LEN):
        angle = (i / _HOVER_LEN) * math.pi * 2
        ox = math.cos(angle) * 0.01
        oy = math.sin(angle) * 0.82
        sc = 0.85 + random.random() * 0.4
        skew = (random.random() - 0.5) * 0.4
        r = random.randint(20, 220)
        g = random.randint(20, 220)
        b = random.randint(20, 220)
        _char_styles.append({
            'fg': [r, g, b, 255],
            'bg': [255, 0, 0, 25],
            'offsetscale': [ox, oy, sc, sc],
            'skew_f': skew,
        })


def _write_hover(hovered: bool):
    r = ni.Region(8, _HOVER_LEN, 1)
    for i, ch in enumerate(_HOVER_TEXT):
        cs = _char_styles[i]
        fg = _FG_HOVER if hovered else cs['fg']
        bg = cs['bg']
        bg_under = _BG_HOVER if hovered else _BG_NORMAL
        ni.setpos(r, i, 0)
        ni.write(r, ch,
                 ni.NiStyle(
                     main=ni.CellStyle(
                         fg=fg,
                         bg=bg,
                         offsetscale=cs['offsetscale'],
                         skew_f=cs['skew_f'],
                     ),
                     under=ni.CellStyle(bg=bg_under),
                 ),
                 ni.LYR_MAIN)
    ni.blitmain(r, x=_HOVER_X, y=_HOVER_Y, w=_HOVER_LEN, h=1, doclear=True)


def setup_part8_hover():
    _gen_char_styles()
    _write_hover(False)


# --- section registry ---
SECTIONS = [
    (lambda: setup_part1(y_offset=5),
     "Part 1: Basic text with under-layer shadow blit"),

    (lambda: setup_part2(y_offset=8),
     "Part 2: Shadow style - offset ghost copy on under layer"),

    (lambda: setup_part3(y_offset=12),
     "Part 3: Box drawing with fill style"),

    (lambda: setup_part4(y_offset=7),
     "Part 4: fillstyle on viewregion directly - override style"),

    (lambda: setup_part5_typer(y_offset=22),
     "Part 5: writeline typer - bold, bg, shadow, skew, tabs"),

    (lambda: setup_part6_scaleoffset(y_offset=20),
     "Part 6: offsetscale - shift and scale per cell"),

    (lambda: setup_part7_superscript(),
     "Part 7: Superscript via offsetscale on over cell"),

    (lambda: setup_part8_hover(),
     "Part 8: Interactive hover - move mouse over HOVER ME"),
]

# --- state ---
_current_section = 0
_hover_state     = False

_ST_LABEL  = ni.NiStyle(main=ni.CellStyle(fg=[30, 30, 30, 255]))
_ST_PROMPT = ni.NiStyle(main=ni.CellStyle(fg=[80, 80, 200, 255]))
_ST_LOOP   = ni.NiStyle(main=ni.CellStyle(fg=[60, 160, 60, 255]))

_PROMPT_ROW_DESC  = 30
_PROMPT_ROW_SPACE = 31


def _clear_prompt():
    cols = ni.viewregion.cols
    ni.clear(ni.viewregion, 0, _PROMPT_ROW_DESC,  cols, 1)
    ni.clear(ni.viewregion, 0, _PROMPT_ROW_SPACE, cols, 1)


def _write_prompt(desc: str, last: bool):
    _clear_prompt()
    ni.setpos(ni.viewregion, 0, _PROMPT_ROW_DESC)
    ni.write(ni.viewregion, desc, _ST_LABEL)

    ni.setpos(ni.viewregion, 0, _PROMPT_ROW_SPACE)
    if last:
        ni.write(ni.viewregion, "press SPACE to loop from start", _ST_LOOP)
    else:
        ni.write(ni.viewregion, "press SPACE to continue", _ST_PROMPT)

    ni.mark_dirty()


def _run_section(idx: int):
    fn, desc = SECTIONS[idx]
    fn()
    last = (idx == len(SECTIONS) - 1)
    _write_prompt(desc, last)


def _reset():
    global _current_section, _hover_state
    _current_section = 0
    _hover_state     = False
    # clear only rows 0..31 instead of full buffer
    ni.clearall(ni.viewregion, 0, 0, ni.viewregion.cols, _PROMPT_ROW_SPACE + 1)
    _run_section(0)




def _update(_rend):
    global _current_section, _hover_state

    if rl.is_key_pressed(rl.KeyboardKey.KEY_SPACE):
        if _current_section < len(SECTIONS) - 1:
            _current_section += 1
            _run_section(_current_section)
        else:
            _reset()

    if _current_section >= 7:
        mx, my = ni.get_mouse_cell_pos()
        hovered = (_HOVER_X <= mx < _HOVER_X + _HOVER_LEN) and (my == _HOVER_Y)
        if hovered != _hover_state:
            _hover_state = hovered
            _write_hover(hovered)
            ni.mark_dirty()


def main():
    global _PROMPT_ROW_DESC, _PROMPT_ROW_SPACE

    ni.init(1280, 720, "ni demo")

    _PROMPT_ROW_DESC  = 30
    _PROMPT_ROW_SPACE = 31

    _run_section(0)

    ni.run(_update)


if __name__ == "__main__":
    main()
