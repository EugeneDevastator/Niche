class Datarx:
    def __init__(self, val=0):
        self._val = val
        self._subs = []

    def get(self):
        return self._val

    def set(self, val, source=None):
        if val == self._val:
            return
        self._val = val
        for fn, owner in self._subs:
            if owner is not source:
                fn(val)

    def subscribe(self, widget):
        self._subs.append((widget.rx_update, widget))
        widget.rx_update(self._val)
