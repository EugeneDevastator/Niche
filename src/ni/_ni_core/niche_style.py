# niche_style.py
import numpy as np
from .layer import (CH_CHAR, CH_FG, CH_BG, CH_STYLE, CH_GEO,
                    LYR_UNDER, LYR_MAIN, LYR_OVER)
from .region import Region


class CellStyle:
    __slots__ = ('fg', 'bg', 'char', 'bold_f', 'skew_f', 'offsetscale', 'get_char_from_main')

    def __init__(self, fg=None, bg=None, char=None,
                 bold_f=None, skew_f=None, offsetscale=None,
                 get_char_from_main=False):
        self.fg                = fg
        self.bg                = bg
        self.char              = char
        self.bold_f            = bold_f
        self.skew_f            = skew_f
        self.offsetscale       = offsetscale
        self.get_char_from_main = get_char_from_main


class NiStyle:
    __slots__ = ('under', 'main', 'over')

    def __init__(self, under=None, main=None, over=None):
        self.under = under if under is not None else CellStyle()
        self.main  = main  if main  is not None else CellStyle()
        self.over  = over  if over  is not None else CellStyle()

    @property
    def layers(self):
        return (self.under, self.main, self.over)


Style = NiStyle
