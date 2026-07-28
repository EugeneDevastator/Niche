# niche_filebrowser.py
import os
import pyray as rl
from .niche_render import Renderer
from .region import Region
from .layer import (LYR_MAIN, LYR_OVER, LYR_UNDER)
from .niche_typer import Typer
from .niche_style import NiStyle, CellStyle

WIN_W = 60
WIN_H = 24
WIN_X = 4
WIN_Y = 2

LIST_Y0 = 3
LIST_Y1 = WIN_H - 2

FG_TITLE  = [240, 240, 240, 255]
FG_DIR    = [80,  140, 220, 255]
FG_FILE   = [30,  30,  30,  255]
FG_SEL    = [240, 240, 240, 255]
FG_STATUS = [100, 100, 100, 255]

BG_TITLE  = [40,  40,  120, 255]
BG_SEL    = [60,  100, 200, 255]
BG_WIN    = [245, 245, 245, 255]
BG_BAR    = [200, 200, 200, 255]


def _make_style(fg=None, bg=None) -> NiStyle:
    return NiStyle(main=CellStyle(fg=fg, bg=bg))


class FileBrowser:
    def __init__(self):
        self._active    = False
        self._region    = None
        self._rend      = None
        self._typer     = None
        self._cwd       = ""
        self._entries   = []
        self._scroll    = 0
        self._cursor    = 0
        self._list_h    = LIST_Y1 - LIST_Y0
        self._result    = None
        self._cancelled = False

    # ------------------------------------------------------------------ public

    def open(self, rend: Renderer, start_path: str = None):
        if self._active:
            return
        self._rend      = rend
        self._typer     = Typer(rend)
        self._active    = True
        self._result    = None
        self._cancelled = False
        self._cwd       = (start_path if start_path and os.path.isdir(start_path)
                           else os.getcwd())

        self._region = Region(0, WIN_W, WIN_H)

        rend.on_mouse_down(self._on_mouse_down)

        self._load_dir()
        self._redraw()

    def close(self):
        if not self._active:
            return
        rend = self._rend
        self._region    = None
        self._active    = False
        self._rend      = None
        self._typer     = None
        try:
            rend._events.input._mouse_down_cbs.remove(self._on_mouse_down)
        except (ValueError, AttributeError):
            pass

    def update(self):
        if not self._active:
            return
        key = rl.get_key_pressed()
        while key != 0:
            if   key == rl.KEY_UP:        self._move_cursor(-1)
            elif key == rl.KEY_DOWN:      self._move_cursor(1)
            elif key == rl.KEY_PAGE_UP:   self._move_cursor(-self._list_h)
            elif key == rl.KEY_PAGE_DOWN: self._move_cursor(self._list_h)
            elif key == rl.KEY_ENTER:     self._activate_current()
            elif key == rl.KEY_BACKSPACE: self._go_up()
            elif key == rl.KEY_ESCAPE:
                self._cancelled = True
                self.close()
                return
            key = rl.get_key_pressed()

    def done(self) -> bool:
        return not self._active and (self._result is not None or self._cancelled)

    def reset(self):
        self._result    = None
        self._cancelled = False

    def result(self) -> str | None:
        return self._result

    # --------------------------------------------------------------- callbacks

    def _on_mouse_down(self, cx: int, cy: int, btn: int):
        if not self._active or btn != 0:
            return
        lx = cx - WIN_X
        ly = cy - WIN_Y
        if not (0 <= lx < WIN_W and 0 <= ly < WIN_H):
            return

        if ly == 0 and lx == WIN_W - 2:
            self._cancelled = True
            self.close()
            return

        if LIST_Y0 <= ly < LIST_Y1 and 1 <= lx < WIN_W - 1:
            idx = self._scroll + (ly - LIST_Y0)
            if 0 <= idx < len(self._entries):
                if idx == self._cursor:
                    self._activate_current()
                else:
                    self._cursor = idx
                    self._redraw()

    # ----------------------------------------------------------------- private

    def _load_dir(self):
        self._entries = []
        self._scroll  = 0
        self._cursor  = 0
        try:
            names = sorted(os.listdir(self._cwd))
        except PermissionError:
            return
        for n in names:
            self._entries.append((n, os.path.isdir(os.path.join(self._cwd, n))))

    def _move_cursor(self, delta: int):
        if not self._entries:
            return
        self._cursor = max(0, min(len(self._entries) - 1, self._cursor + delta))
        if self._cursor < self._scroll:
            self._scroll = self._cursor
        elif self._cursor >= self._scroll + self._list_h:
            self._scroll = self._cursor - self._list_h + 1
        self._redraw()

    def _activate_current(self):
        if not self._entries:
            return
        name, is_dir = self._entries[self._cursor]
        full = os.path.join(self._cwd, name)
        if is_dir:
            self._cwd = full
            self._load_dir()
            self._redraw()
        else:
            self._result = full
            self.close()

    def _go_up(self):
        parent = os.path.dirname(self._cwd)
        if parent != self._cwd:
            self._cwd = parent
            self._load_dir()
            self._redraw()

    def _wt(self, x, y, text, fg=None, bg=None):
        t = self._typer
        t.SetRegion(self._region)
        t.SetPos(x, y)
        t.SetStyle(_make_style(fg=fg or FG_FILE, bg=bg or BG_WIN))
        t.Write(text)

    def _fill_row(self, y, bg):
        self._wt(0, y, " " * WIN_W, fg=[0, 0, 0, 0], bg=bg)

    def _redraw(self):
        rend = self._rend
        r    = self._region
        W    = WIN_W

        r.clear_all(0, 0, W, WIN_H)

        # title bar
        self._fill_row(0, BG_TITLE)
        self._wt(2,     0, " File Browser ", fg=FG_TITLE,          bg=BG_TITLE)
        self._wt(W - 2, 0, "X",              fg=[255, 80, 80, 255], bg=BG_TITLE)

        # path bar
        self._fill_row(1, BG_BAR)
        self._wt(1, 1, self._cwd[:W - 2], fg=[60, 60, 60, 255], bg=BG_BAR)

        # column header
        self._fill_row(2, BG_WIN)
        self._wt(1, 2, "Name", fg=FG_STATUS, bg=BG_WIN)

        # list rows
        for i in range(self._list_h):
            row_y = LIST_Y0 + i
            self._fill_row(row_y, BG_WIN)
            idx = self._scroll + i
            if idx >= len(self._entries):
                continue
            name, is_dir = self._entries[idx]
            sel    = (idx == self._cursor)
            bg     = BG_SEL if sel else BG_WIN
            fg     = FG_SEL if sel else (FG_DIR if is_dir else FG_FILE)
            prefix = "[D] " if is_dir else "    "
            label  = (prefix + name)[:W - 2]
            self._wt(1, row_y, f"{label:<{W - 2}}", fg=fg, bg=bg)

        # status bar
        self._fill_row(WIN_H - 2, BG_BAR)
        total  = len(self._entries)
        status = f" {self._cursor + 1}/{total}  Enter=open  Bksp=up  Esc=cancel"
        self._wt(0, WIN_H - 2, status[:W], fg=FG_STATUS, bg=BG_BAR)

        # hint bar
        self._fill_row(WIN_H - 1, BG_WIN)
        self._wt(1, WIN_H - 1, "Arrows / PgUp / PgDn to navigate",
                 fg=FG_STATUS, bg=BG_WIN)

        rend.blit(r, x=WIN_X, y=WIN_Y, w=W, h=WIN_H, doclear=True)
        rend.mark_dirty()
