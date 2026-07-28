# nidemo_ui2.py
import ni
import niui

_root         = None
_status_label = None

def setup():
    global _root, _status_label

    def on_ok():
        _status_label.text = "OK pressed    "

    def on_cancel():
        _status_label.text = "Cancel pressed"

    def on_check(state):
        _status_label.text = f"check={state}      "

    pa  = niui.panel(38, 10)
    col = niui.layout_v(gap=1)
    col.add(niui.label("Demo Panel A", w=36))
    col.add(niui.label("─" * 36, w=36))

    row_cb = niui.layout_h(gap=1)
    row_cb.add(niui.checkbox(cb=on_check))
    row_cb.add(niui.label("toggle me", w=12))
    col.add(row_cb)

    row_btn = niui.layout_h(gap=2)
    row_btn.add(niui.button("OK",     cb=on_ok))
    row_btn.add(niui.button("Cancel", cb=on_cancel))
    col.add(row_btn)

    _status_label = niui.label("               ", w=20)
    col.add(_status_label)
    pa.add(col, 1, 1)

    pb = niui.panel(38, 5)
    pb.add(niui.label("Demo Panel B", w=36), 1, 1)
    pb.add(niui.label("Tab / Ctrl+Tab to move focus", w=36), 1, 3)

    _root = niui.UIRoot(ni.viewregion)
    _root.add(pa, x=4, y=2)
    _root.add(pb, x=4, y=14)
    _root.draw()


def update(_rend):
    _root.update()


def main():
    ni.init(1280, 720, "niui demo")
    setup()
    ni.run(update)


if __name__ == "__main__":
    main()
