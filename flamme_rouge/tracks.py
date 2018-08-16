# -*- coding: utf-8 -*-

''' tracks '''

from .core import MountainDown, MountainUp, Section, Track

_SEC = (Section,)
_UP = (MountainUp,)
_DOWN = (MountainDown,)

AVENUE_CORSO_PASEO = Track.from_string(_SEC * 78)
FIRENZE_MILANO = Track.from_string(
    _SEC * 22 + _UP * 5 + _DOWN * 3 + _SEC * 16 + _UP * 7 + _DOWN * 3 + _SEC * 22)
LA_HAUT_MONTAGNE = Track.from_string(
    _SEC * 36 + _UP * 7 + _DOWN * 5 + _SEC * 14 + _UP * 12 + _SEC * 4,
    finish=-4)
PLATEAUX_DE_WALLONIE = Track.from_string(
    _SEC * 16 + _UP * 3 + _DOWN * 3 + _SEC * 6
    + _UP * 2 + _DOWN * 2 + _SEC * 34 + _UP * 2 + _SEC * 10,
    start=4)
