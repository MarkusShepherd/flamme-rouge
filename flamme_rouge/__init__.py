# -*- coding: utf-8 -*-

""" init """

from .__version__ import VERSION, __version__
from .tracks import (
    AVENUE_CORSO_PASEO,
    FIRENZE_MILANO,
    LA_CLASSICISSIMA,
    LA_HAUT_MONTAGNE,
    LE_COL_DU_BALLON,
    PLATEAUX_DE_WALLONIE,
    RONDE_VAN_WEVELGEM,
    STAGE_7,
    STAGE_7_5_6,
    STAGE_9,
    ALL_TRACKS,
)

try:
    from colorama import init

    init()

except Exception:
    pass
