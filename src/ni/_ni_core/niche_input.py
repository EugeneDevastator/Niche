# niche_input.py - keyboard, mouse, scroll input handling
import pyray as rl
from typing import Callable

ZOOM_STEP = 0.1

_MOUSE_BUTTONS = (
    (0, rl.MOUSE_BUTTON_LEFT),
    (1, rl.MOUSE_BUTTON_RIGHT),
    (2, rl.MOUSE_BUTTON_MIDDLE),
)


class InputHandler:
    def __init__(self):
        self._mouse_down_cbs: list[Callable] = []
        self._mouse_up_cbs:   list[Callable] = []

    def on_mouse_down(self, fn: Callable):
        self._mouse_down_cbs.append(fn)

    def on_mouse_up(self, fn: Callable):
        self._mouse_up_cbs.append(fn)

    def process(self, renderer):
        ctrl_down = (rl.is_key_down(rl.KEY_LEFT_CONTROL) or
                     rl.is_key_down(rl.KEY_RIGHT_CONTROL))
        scroll = rl.get_mouse_wheel_move()

        if ctrl_down and scroll != 0.0:
            renderer._apply_zoom(scroll * ZOOM_STEP)

        for btn, rl_btn in _MOUSE_BUTTONS:
            if rl.is_mouse_button_pressed(rl_btn):
                cx, cy = renderer.get_mouse_cell_pos()
                for fn in self._mouse_down_cbs:
                    fn(cx, cy, btn)
            if rl.is_mouse_button_released(rl_btn):
                cx, cy = renderer.get_mouse_cell_pos()
                for fn in self._mouse_up_cbs:
                    fn(cx, cy, btn)



class DragDropHandler:
    def __init__(self):
        self._drop_cbs: list[Callable] = []

    def on_file_drop(self, fn: Callable):
        self._drop_cbs.append(fn)

    def process(self, renderer):
        if not rl.is_file_dropped():
            return
        dropped = rl.load_dropped_files()
        paths = []
        for i in range(dropped.count):
            raw = dropped.paths[i]
            try:
                paths.append(rl.ffi.string(raw).decode('utf-8', errors='replace'))
            except Exception:
                paths.append(str(raw))
        rl.unload_dropped_files(dropped)
        cx, cy = renderer.get_mouse_cell_pos()
        for fn in self._drop_cbs:
            fn(paths, cx, cy)
            


class EventBus:
    def __init__(self):
        self.input    = InputHandler()
        self.dragdrop = DragDropHandler()

    def on_mouse_down(self, fn: Callable):
        self.input.on_mouse_down(fn)

    def on_mouse_up(self, fn: Callable):
        self.input.on_mouse_up(fn)

    def on_file_drop(self, fn: Callable):
        self.dragdrop.on_file_drop(fn)

    def process(self, renderer):
        self.input.process(renderer)
        self.dragdrop.process(renderer)