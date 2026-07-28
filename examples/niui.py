# niui.py
import ni
from ni import Region, LYR_MAIN, LYR_OVER

C_TEXT      = [20,  20,  20,  255]
C_BG        = [235, 235, 235, 255]
C_BORDER    = [160, 160, 160, 255]
C_BTN_BG    = [210, 210, 210, 255]
C_BTN_HOV   = [180, 200, 240, 255]
C_BTN_PRESS = [140, 170, 220, 255]
C_FOCUS_BG  = [200, 220, 255, 255]
C_FOCUS_OVR = [160, 210, 255, 80]
C_CURSOR_FG = [20,  20,  20,  255]
C_CURSOR_BG = [0, 220,  255, 180]

_rid = 2000
def _new_rid():
    global _rid; _rid += 1; return _rid

def _st(fg=None, bg=None):
    return ni.NiStyle(main=ni.CellStyle(fg=fg, bg=bg))

def _put(reg, x, y, text, fg=None, bg=None):
    st = _st(fg, bg) if (fg or bg) else None
    ni.setpos(reg, x, y)
    ni.write(reg, text, st)

def _draw_focus_over(elem, on: bool):
    if elem._target is None:
        return
    st_over  = ni.NiStyle(over=ni.CellStyle(bg=C_FOCUS_OVR, char='_', get_char_from_main=False))
    st_clear = ni.NiStyle(over=ni.CellStyle(bg=[0,0,0,0], char=' '))
    st = st_over if on else st_clear
    ni.fillstyle(elem._target, elem._bx, elem._by, elem.w, elem.h, st)
    ni.mark_dirty()


# ── mouse cursor ──────────────────────────────────────────────────────────────
class MouseCursor:
    """Draws a 1-cell highlight on LYR_OVER tracking the mouse cell position."""
    GLYPH = ' ' #'▌'

    def __init__(self, target: Region):
        self._target  = target
        self._prev_cx = -1
        self._prev_cy = -1

    def _clear_prev(self):
        if self._prev_cx < 0:
            return
        ni.fillstyle(
            self._target,
            self._prev_cx, self._prev_cy, 1, 1,
            ni.NiStyle(over=ni.CellStyle(bg=[0,0,0,0], fg=[0,0,0,0], char=' '))
        )

    def _draw_at(self, cx, cy):
        cols, rows = self._target.cols, self._target.rows
        if cx < 0 or cy < 0 or cx >= cols or cy >= rows:
            return
        ni.fillstyle(
            self._target,
            cx, cy, 1, 1,
            ni.NiStyle(over=ni.CellStyle(
                bg=C_CURSOR_BG,
                fg=C_CURSOR_FG,
                char=self.GLYPH,
            ))
        )

    def update(self):
        cx, cy = ni.get_mouse_cell_pos()
        if cx == self._prev_cx and cy == self._prev_cy:
            return
        self._clear_prev()
        self._draw_at(cx, cy)
        self._prev_cx = cx
        self._prev_cy = cy
        ni.mark_dirty()


# ── base ──────────────────────────────────────────────────────────────────────
class Elem:
    def __init__(self, w, h):
        self.w = w
        self.h = h
        self._reg    = None
        self._bx     = 0
        self._by     = 0
        self._target = None
        self._dirty  = True

    def _ensure_reg(self):
        if self._reg is None:
            self._reg = ni.region(_new_rid(), self.w, self.h)

    def _on_draw(self): pass

    def _self_redraw(self):
        if not self._dirty or self._reg is None or self._target is None:
            return
        self._on_draw()
        ni.blit(self._target, self._reg, x=self._bx, y=self._by, w=self.w, h=self.h)
        ni.mark_dirty()
        self._dirty = False

    def _mark(self):
        self._dirty = True

    def draw(self, target: Region, x, y):
        self._target = target
        self._bx = x
        self._by = y
        self._ensure_reg()
        self._dirty = True
        self._self_redraw()

    def update(self): pass
    def focusable(self): return False


# ── label ─────────────────────────────────────────────────────────────────────
class Label(Elem):
    def __init__(self, text, w=0):
        super().__init__(w if w > 0 else len(text), 1)
        self._text = text

    @property
    def text(self): return self._text

    @text.setter
    def text(self, v):
        if v == self._text: return
        self._text = v
        self._mark()
        self._self_redraw()

    def _on_draw(self):
        ni.clear(self._reg, lyr=LYR_MAIN)
        _put(self._reg, 0, 0, self._text[:self.w], fg=C_TEXT)


# ── button ────────────────────────────────────────────────────────────────────
class Button(Elem):
    def __init__(self, label, cb=None):
        super().__init__(len(label) + 4, 1)
        self.label    = label
        self.cb       = cb
        self.focused  = False
        self._hov     = False
        self._pressed = False

    def focusable(self): return True

    def _bg(self):
        if self._pressed:             return C_BTN_PRESS
        if self._hov or self.focused: return C_BTN_HOV
        return C_BTN_BG

    def _on_draw(self):
        ni.clear(self._reg, lyr=LYR_MAIN)
        bg    = self._bg()
        inner = ' ' * (self.w - 2)
        _put(self._reg, 0, 0, '[' + inner + ']', fg=C_TEXT, bg=bg)
        tx = 1 + max(0, (self.w - 2 - len(self.label)) // 2)
        _put(self._reg, tx, 0, self.label, fg=C_TEXT, bg=bg)

    def update(self):
        import pyray as rl
        cx, cy = ni.get_mouse_cell_pos()
        hov = (self._bx <= cx < self._bx + self.w) and cy == self._by
        changed = hov != self._hov
        self._hov = hov

        if rl.is_mouse_button_pressed(rl.MOUSE_BUTTON_LEFT) and hov:
            self._pressed = True; changed = True

        if rl.is_mouse_button_released(rl.MOUSE_BUTTON_LEFT) and self._pressed:
            self._pressed = False
            if hov and self.cb: self.cb()
            changed = True

        if self.focused and rl.is_key_pressed(rl.KEY_ENTER) and self.cb:
            self.cb()

        if changed:
            self._mark(); self._self_redraw()


# ── checkbox ──────────────────────────────────────────────────────────────────
class Checkbox(Elem):
    def __init__(self, checked=False, cb=None):
        super().__init__(3, 1)
        self.checked = checked
        self.cb      = cb
        self.focused = False
        self._hov    = False

    def focusable(self): return True

    def _on_draw(self):
        ni.clear(self._reg, lyr=LYR_MAIN)
        bg   = C_FOCUS_BG if (self._hov or self.focused) else C_BG
        mark = 'x' if self.checked else ' '
        _put(self._reg, 0, 0, f'[{mark}]', fg=C_TEXT, bg=bg)

    def _toggle(self):
        self.checked = not self.checked
        if self.cb: self.cb(self.checked)
        self._mark(); self._self_redraw()

    def update(self):
        import pyray as rl
        cx, cy = ni.get_mouse_cell_pos()
        hov = (self._bx <= cx < self._bx + self.w) and cy == self._by
        changed = hov != self._hov
        self._hov = hov

        if rl.is_mouse_button_pressed(rl.MOUSE_BUTTON_LEFT) and hov:
            self._toggle(); return
        if self.focused and rl.is_key_pressed(rl.KEY_SPACE):
            self._toggle(); return
        if changed:
            self._mark(); self._self_redraw()


# ── panel ─────────────────────────────────────────────────────────────────────
class Panel(Elem):
    def __init__(self, w, h, border=True):
        super().__init__(w, h)
        self.border    = border
        self._children = []

    def add(self, elem: Elem, lx=0, ly=0):
        self._children.append((elem, lx, ly))
        return self

    def focusable_children(self):
        out = []
        for e, _, _ in self._children:
            out += _collect_focusable(e)
        return out

    def _on_draw(self):
        ni.clearall(self._reg)
        ni.fillstyle(self._reg, 0, 0, self.w, self.h, _st(bg=C_BG))
        if self.border:
            top = '┌' + '─' * (self.w - 2) + '┐'
            bot = '└' + '─' * (self.w - 2) + '┘'
            _put(self._reg, 0, 0,        top, fg=C_BORDER)
            _put(self._reg, 0, self.h-1, bot, fg=C_BORDER)
            for r in range(1, self.h - 1):
                _put(self._reg, 0,        r, '│', fg=C_BORDER)
                _put(self._reg, self.w-1, r, '│', fg=C_BORDER)

    def draw(self, target: Region, x, y):
        self._target = target
        self._bx = x; self._by = y
        self._ensure_reg()
        self._dirty = True
        self._self_redraw()
        for elem, lx, ly in self._children:
            elem.draw(target, x + lx, y + ly)

    def update(self):
        for elem, _, _ in self._children:
            elem.update()


# ── layouts ───────────────────────────────────────────────────────────────────
class LayoutV(Elem):
    def __init__(self, gap=0):
        super().__init__(0, 0)
        self._items = []
        self.gap    = gap

    def add(self, elem: Elem):
        self._items.append(elem)
        self.h += elem.h + (self.gap if len(self._items) > 1 else 0)
        self.w  = max(self.w, elem.w)
        return self

    def draw(self, target: Region, x, y):
        self._target = target
        cy = y
        for elem in self._items:
            elem.draw(target, x, cy)
            cy += elem.h + self.gap

    def update(self):
        for e in self._items: e.update()


class LayoutH(Elem):
    def __init__(self, gap=1):
        super().__init__(0, 0)
        self._items = []
        self.gap    = gap

    def add(self, elem: Elem):
        self._items.append(elem)
        self.w += elem.w + (self.gap if len(self._items) > 1 else 0)
        self.h  = max(self.h, elem.h)
        return self

    def draw(self, target: Region, x, y):
        self._target = target
        cx = x
        for elem in self._items:
            elem.draw(target, cx, y)
            cx += elem.w + self.gap

    def update(self):
        for e in self._items: e.update()


# ── helpers ───────────────────────────────────────────────────────────────────
def _collect_focusable(elem):
    out = []
    if elem.focusable():
        out.append(elem)
    if hasattr(elem, '_items'):
        for e in elem._items:
            out += _collect_focusable(e)
    if hasattr(elem, '_children'):
        for e, _, _ in elem._children:
            out += _collect_focusable(e)
    return out


# ── focus manager ─────────────────────────────────────────────────────────────
class _FocusMgr:
    def __init__(self):
        self._panels = []
        self._pi     = 0
        self._focus  = None

    def reg(self, panel: Panel):
        self._panels.append(panel)
        if len(self._panels) == 1:
            self._try_first()

    def _try_first(self):
        if not self._panels: return
        fc = self._panels[self._pi].focusable_children()
        if fc: self._set(fc[0])

    def _set(self, elem):
        if self._focus:
            self._focus.focused = False
            self._focus._mark()
            self._focus._self_redraw()
            _draw_focus_over(self._focus, False)
        self._focus = elem
        if elem:
            elem.focused = True
            elem._mark()
            elem._self_redraw()
            _draw_focus_over(elem, True)

    def process(self):
        import pyray as rl
        if not rl.is_key_pressed(rl.KEY_TAB): return
        ctrl = rl.is_key_down(rl.KEY_LEFT_CONTROL) or rl.is_key_down(rl.KEY_RIGHT_CONTROL)
        if ctrl:
            self._pi = (self._pi + 1) % max(1, len(self._panels))
            self._try_first()
        else:
            if not self._panels: return
            fc = self._panels[self._pi].focusable_children()
            if not fc: return
            idx = fc.index(self._focus) if self._focus in fc else -1
            self._set(fc[(idx + 1) % len(fc)])


# ── UIRoot ────────────────────────────────────────────────────────────────────
class UIRoot:
    def __init__(self, target: Region):
        self._target = target
        self._items  = []
        self._focus  = _FocusMgr()
        self._cursor = MouseCursor(target)

    def add(self, elem: Elem, x=0, y=0):
        self._items.append((elem, x, y))
        if isinstance(elem, Panel):
            self._focus.reg(elem)
        return self

    def draw(self):
        for elem, x, y in self._items:
            elem.draw(self._target, x, y)

    def update(self):
        self._focus.process()
        for elem, _, _ in self._items:
            elem.update()
        self._cursor.update()


# ── factory ───────────────────────────────────────────────────────────────────
def panel(w, h, border=True):         return Panel(w, h, border)
def label(text, w=0):                 return Label(text, w)
def button(text, cb=None):            return Button(text, cb)
def checkbox(checked=False, cb=None): return Checkbox(checked, cb)
def layout_v(gap=0):                  return LayoutV(gap)
def layout_h(gap=1):                  return LayoutH(gap)
