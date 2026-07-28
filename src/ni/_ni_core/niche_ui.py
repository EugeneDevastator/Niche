# niche_ui.py
import pyray as rl
from .niche_render import Renderer
from .region import Region
from .layer import LYR_MAIN, LYR_OVER, LYR_UNDER, CH_CHAR
from .niche_typer import Typer
from .niche_style import NiStyle, CellStyle, apply_style_to_region

# ─── palette (light theme) ───────────────────────────────────────────────────
C_TEXT      = [20,  20,  20,  255]
C_DIM       = [120, 120, 120, 255]
C_BG        = [240, 240, 240, 255]
C_BORDER    = [160, 160, 160, 255]
C_FOCUS_BG  = [200, 220, 255, 255]
C_BTN_BG    = [210, 210, 210, 255]
C_BTN_HOV   = [180, 200, 240, 255]
C_BTN_PRESS = [140, 170, 220, 255]

ALIGN_LEFT   = 'left'
ALIGN_CENTER = 'center'
ALIGN_RIGHT  = 'right'

_region_counter = 1000

def _new_rid():
    global _region_counter
    _region_counter += 1
    return _region_counter


def _make_style(fg=None, bg=None) -> NiStyle:
    return NiStyle(main=CellStyle(fg=fg, bg=bg))


def _write_to_region(region: Region, x: int, y: int, text: str,
                     fg=None, bg=None):
    region.layer(LYR_MAIN).write_text(x, y, text)
    if fg is not None or bg is not None:
        n = len(text)
        apply_style_to_region(region, x, y, n, 1,
                              _make_style(fg=fg, bg=bg))


# ─── focus manager ────────────────────────────────────────────────────────────
class FocusManager:
    def __init__(self):
        self.panels = []
        self._panel_idx  = 0
        self._focus_elem = None

    def register_panel(self, panel):
        self.panels.append(panel)
        if len(self.panels) == 1:
            self._panel_idx = 0
            self._try_focus_first()

    def _try_focus_first(self):
        if not self.panels:
            return
        p = self.panels[self._panel_idx]
        focusable = p.focusable_children()
        if focusable:
            self._set_focus(focusable[0])

    def _set_focus(self, elem):
        if self._focus_elem is not None:
            self._focus_elem.focused = False
            self._focus_elem.on_draw()
        self._focus_elem = elem
        if elem is not None:
            elem.focused = True
            elem.on_draw()

    def process_keys(self):
        ctrl = rl.is_key_down(rl.KEY_LEFT_CONTROL) or rl.is_key_down(rl.KEY_RIGHT_CONTROL)
        if rl.is_key_pressed(rl.KEY_TAB):
            if ctrl:
                self._next_panel()
            else:
                self._next_sibling()

    def _next_panel(self):
        if not self.panels:
            return
        self._panel_idx = (self._panel_idx + 1) % len(self.panels)
        self._try_focus_first()

    def _next_sibling(self):
        if not self.panels:
            return
        p = self.panels[self._panel_idx]
        focusable = p.focusable_children()
        if not focusable:
            return
        if self._focus_elem in focusable:
            idx = focusable.index(self._focus_elem)
            nxt = focusable[(idx + 1) % len(focusable)]
        else:
            nxt = focusable[0]
        self._set_focus(nxt)

    def focused(self, elem) -> bool:
        return self._focus_elem is elem


_focus_mgr = FocusManager()


# ─── base element ─────────────────────────────────────────────────────────────
class Element:
    def __init__(self, w: int, h: int):
        self.w = w
        self.h = h
        self.focused  = False
        self._region  = None
        self._rend    = None
        self._blit_x  = 0
        self._blit_y  = 0

    def get_size(self):
        return self.w, self.h

    def _ensure_region(self, rend: Renderer):
        if self._region is None:
            self._region = Region(_new_rid(), self.w, self.h)
            self._rend   = rend

    def draw(self, rend: Renderer, x: int, y: int, w: int = None, h: int = None):
        self._ensure_region(rend)
        self._blit_x = x
        self._blit_y = y
        if w is None: w = self.w
        if h is None: h = self.h
        self.on_draw()
        rend.blit(self._region, x=x, y=y, w=w, h=h)

    def redraw(self):
        if self._rend is None or self._region is None:
            return
        self.on_draw()
        self._rend.blit(self._region, x=self._blit_x, y=self._blit_y,
                        w=self.w, h=self.h)

    def on_draw(self):
        pass

    def is_focusable(self) -> bool:
        return False

    def update(self, rend: Renderer):
        pass


# ─── label ────────────────────────────────────────────────────────────────────
class Label(Element):
    def __init__(self, text: str, width: int = 0, align: str = ALIGN_LEFT):
        w = width if width > 0 else len(text)
        super().__init__(w, 1)
        self.text  = text
        self.align = align

    def _text_x(self) -> int:
        if self.align == ALIGN_LEFT:
            return 0
        elif self.align == ALIGN_RIGHT:
            return max(0, self.w - len(self.text))
        else:
            return max(0, (self.w - len(self.text)) // 2)

    def _fx(self) -> float:
        if self.align != ALIGN_CENTER:
            return 0.0
        gap = self.w - len(self.text)
        return 0.5 if (gap > 0 and gap % 2 == 1) else 0.0

    def on_draw(self):
        if self._region is None:
            return
        import numpy as np
        self._region.array(LYR_MAIN)[:] = 0.0
        _write_to_region(self._region, self._text_x(), 0, self.text, fg=C_TEXT)

    def draw(self, rend: Renderer, x: int, y: int, w: int = None, h: int = None):
        self._ensure_region(rend)
        self._blit_x = x
        self._blit_y = y
        if w is None: w = self.w
        if h is None: h = self.h
        self.on_draw()
        rend.blit(self._region, x=x, y=y, w=w, h=h, fx=self._fx())

    def redraw(self):
        if self._rend is None or self._region is None:
            return
        self.on_draw()
        self._rend.blit(self._region, x=self._blit_x, y=self._blit_y,
                        w=self.w, h=self.h, fx=self._fx())


# ─── button ───────────────────────────────────────────────────────────────────
class Button(Element):
    def __init__(self, label: str, callback=None):
        w = len(label) + 4
        super().__init__(w, 1)
        self.label    = label
        self.callback = callback
        self._pressed = False
        self._hovered = False

    def is_focusable(self) -> bool:
        return True

    def _bg(self):
        if self._pressed:          return C_BTN_PRESS
        if self._hovered or self.focused: return C_BTN_HOV
        return C_BTN_BG

    def on_draw(self):
        if self._region is None:
            return
        self._region.array(LYR_MAIN)[:] = 0.0
        bg = self._bg()
        _write_to_region(self._region, 0, 0, '[', fg=C_TEXT, bg=bg)
        _write_to_region(self._region, self.w - 1, 0, ']', fg=C_TEXT, bg=bg)
        _write_to_region(self._region, 1, 0, ' ' * (self.w - 2), fg=C_TEXT, bg=bg)
        tx = 1 + max(0, (self.w - 2 - len(self.label)) // 2)
        _write_to_region(self._region, tx, 0, self.label, fg=C_TEXT, bg=bg)

    def _blit(self):
        self._rend.blit(self._region, x=self._blit_x, y=self._blit_y,
                        w=self.w, h=1)

    def update(self, rend: Renderer):
        cx, cy = rend.get_mouse_cell_pos()
        bx, by = self._blit_x, self._blit_y
        hover  = (bx <= cx < bx + self.w) and (cy == by)

        prev_hov      = self._hovered
        self._hovered = hover

        if rl.is_mouse_button_pressed(rl.MOUSE_BUTTON_LEFT) and hover:
            self._pressed = True
            self.on_draw(); self._blit()

        if rl.is_mouse_button_released(rl.MOUSE_BUTTON_LEFT) and self._pressed:
            self._pressed = False
            if hover and self.callback:
                self.callback()
            self.on_draw(); self._blit()

        if self.focused and rl.is_key_pressed(rl.KEY_ENTER):
            if self.callback:
                self.callback()

        if prev_hov != self._hovered:
            self.on_draw(); self._blit()


# ─── checkbox ─────────────────────────────────────────────────────────────────
class Checkbox(Element):
    def __init__(self, checked: bool = False, callback=None):
        super().__init__(3, 1)
        self.checked  = checked
        self.callback = callback
        self._hovered = False

    def is_focusable(self) -> bool:
        return True

    def on_draw(self):
        if self._region is None:
            return
        self._region.array(LYR_MAIN)[:] = 0.0
        bg   = C_BTN_HOV if (self._hovered or self.focused) else C_BG
        mark = 'x' if self.checked else ' '
        _write_to_region(self._region, 0, 0, f'[{mark}]', fg=C_TEXT, bg=bg)

    def _blit(self):
        self._rend.blit(self._region, x=self._blit_x, y=self._blit_y,
                        w=self.w, h=1)

    def _toggle(self, rend: Renderer):
        self.checked = not self.checked
        if self.callback:
            self.callback(self.checked)
        self.on_draw(); self._blit()

    def update(self, rend: Renderer):
        cx, cy = rend.get_mouse_cell_pos()
        bx, by = self._blit_x, self._blit_y
        hover  = (bx <= cx < bx + self.w) and (cy == by)

        prev_hov      = self._hovered
        self._hovered = hover

        if rl.is_mouse_button_pressed(rl.MOUSE_BUTTON_LEFT) and hover:
            self._toggle(rend)

        if self.focused and rl.is_key_pressed(rl.KEY_SPACE):
            self._toggle(rend)

        if prev_hov != self._hovered:
            self.on_draw(); self._blit()


# ─── panel ────────────────────────────────────────────────────────────────────
class Panel(Element):
    def __init__(self, w: int, h: int, border: bool = True):
        super().__init__(w, h)
        self.border    = border
        self._children = []

    def add(self, elem: Element, lx: int, ly: int):
        self._children.append((elem, lx, ly))

    def focusable_children(self):
        return [e for e, _, _ in self._children if e.is_focusable()]

    def on_draw(self):
        if self._region is None:
            return
        self._region.array(LYR_MAIN)[:] = 0.0
        if self.border:
            _draw_border(self._region, self.w, self.h)

    def draw(self, rend: Renderer, x: int, y: int, w: int = None, h: int = None):
        self._ensure_region(rend)
        self._blit_x = x
        self._blit_y = y
        self.on_draw()
        rend.blit(self._region, x=x, y=y, w=self.w, h=self.h)
        for elem, lx, ly in self._children:
            elem.draw(rend, x + lx, y + ly)

    def update(self, rend: Renderer):
        _focus_mgr.process_keys()
        for elem, _, _ in self._children:
            elem.update(rend)


# ─── horizontal layout ────────────────────────────────────────────────────────
class LayoutH(Element):
    def __init__(self, gap: int = 1):
        super().__init__(0, 1)
        self._items = []
        self.gap    = gap

    def add(self, elem: Element):
        self._items.append(elem)
        ew, eh = elem.get_size()
        self.w += ew + (self.gap if len(self._items) > 1 else 0)
        self.h  = max(self.h, eh)

    def draw(self, rend: Renderer, x: int, y: int, w: int = None, h: int = None):
        cx = x
        for elem in self._items:
            ew, eh = elem.get_size()
            elem.draw(rend, cx, y, ew, eh)
            cx += ew + self.gap

    def update(self, rend: Renderer):
        for elem in self._items:
            elem.update(rend)

    def is_focusable(self) -> bool:
        return False


# ─── vertical layout ──────────────────────────────────────────────────────────
class LayoutV(Element):
    def __init__(self, gap: int = 0):
        super().__init__(0, 0)
        self._items = []
        self.gap    = gap

    def add(self, elem: Element):
        self._items.append(elem)
        ew, eh = elem.get_size()
        self.h += eh + (self.gap if len(self._items) > 1 else 0)
        self.w  = max(self.w, ew)

    def draw(self, rend: Renderer, x: int, y: int, w: int = None, h: int = None):
        cy = y
        for elem in self._items:
            ew, eh = elem.get_size()
            elem.draw(rend, x, cy, ew, eh)
            cy += eh + self.gap

    def update(self, rend: Renderer):
        for elem in self._items:
            elem.update(rend)

    def is_focusable(self) -> bool:
        return False


# ─── cursor ───────────────────────────────────────────────────────────────────
import numpy as np

class Cursor:
    """
    Tracks a cell position on a given layer index.
    Before update: restores saved content under cursor.
    Before draw:   saves content, applies style.
    """
    def __init__(self, w: int = 1, h: int = 1,
                 layer_idx: int = LYR_OVER,
                 style: NiStyle = None):
        self.x        = 0
        self.y        = 0
        self.w        = w
        self.h        = h
        self._lyr     = layer_idx
        self._style   = style
        self._saved   = None   # numpy slice copy
        self._rend    = None
        self._placed  = False

    def _layer_arr(self) -> np.ndarray:
        return self._rend.layers[self._lyr].da

    def restore(self):
        """Put saved content back before update."""
        if not self._placed or self._saved is None or self._rend is None:
            return
        arr = self._layer_arr()
        r0, r1 = self.y, self.y + self.h
        c0, c1 = self.x, self.x + self.w
        r1 = min(r1, arr.shape[0]); c1 = min(c1, arr.shape[1])
        if r1 > r0 and c1 > c0:
            arr[r0:r1, c0:c1] = self._saved[:r1-r0, :c1-c0]
        self._rend._mark_db_rect_dirty(c0, r0, c1 - c0, r1 - r0)
        self._placed = False

    def apply(self, rend: Renderer, x: int, y: int):
        """Save content at (x,y) then stamp style."""
        self._rend = rend
        self.x = x
        self.y = y
        arr = self._layer_arr()
        r0, r1 = y, y + self.h
        c0, c1 = x, x + self.w
        r1 = min(r1, arr.shape[0]); c1 = min(c1, arr.shape[1])
        if r1 <= r0 or c1 <= c0:
            return
        self._saved = arr[r0:r1, c0:c1].copy()
        # apply style
        if self._style is not None:
            from niche_style import CH_BG as _CH_BG, CH_FG as _CH_FG
            from layer import CH_BG, CH_FG
            cs = self._style.main
            if cs is not None:
                if cs.bg is not None:
                    arr[r0:r1, c0:c1, CH_BG, :] = cs.bg
                if cs.fg is not None:
                    arr[r0:r1, c0:c1, CH_FG, :] = cs.fg
        rend._mark_db_rect_dirty(c0, r0, c1 - c0, r1 - r0)
        self._placed = True


# ─── border helper ────────────────────────────────────────────────────────────
def _draw_border(region: Region, w: int, h: int):
    _write_to_region(region, 0, 0, '┌' + '─' * (w - 2) + '┐', fg=C_BORDER)
    _write_to_region(region, 0, h - 1, '└' + '─' * (w - 2) + '┘', fg=C_BORDER)
    for row in range(1, h - 1):
        _write_to_region(region, 0,     row, '│', fg=C_BORDER)
        _write_to_region(region, w - 1, row, '│', fg=C_BORDER)


# ─── factory helpers ──────────────────────────────────────────────────────────
def make_panel(w, h, border=True):       return Panel(w, h, border)
def make_label(text, width=0, align=ALIGN_LEFT): return Label(text, width, align)
def make_button(label, callback=None):   return Button(label, callback)
def make_checkbox(checked=False, callback=None): return Checkbox(checked, callback)
def make_layout_h(gap=1):               return LayoutH(gap)
def make_layout_v(gap=0):               return LayoutV(gap)
def make_text(text):                    return Label(text)

def make_cursor(w=1, h=1, layer_idx=LYR_OVER, style=None):
    return Cursor(w=w, h=h, layer_idx=layer_idx, style=style)

def register_panel(panel: Panel):
    _focus_mgr.register_panel(panel)
