# -*- coding: utf-8 -*-

""" actions """

from typing import TYPE_CHECKING
from dataclasses import dataclass

if TYPE_CHECKING:
    # pylint: disable=cyclic-import,unused-import
    from .cards import Card
    from .teams import Cyclist


# pylint: disable=too-few-public-methods
@dataclass(frozen=True)
class Action:
    """ an action in Flamme Rouge """

    cyclist: "Cyclist"


@dataclass(frozen=True)
class SelectStartPositionAction(Action):
    """ select starting position """

    position: int


@dataclass(frozen=True)
class RaceAction(Action):
    """ an action during the race phase """


@dataclass(frozen=True)
class SelectCyclistAction(RaceAction):
    """ select a cyclist to race """


@dataclass(frozen=True)
class SelectCardAction(RaceAction):
    """ select a card from cyclist's hand """

    card: "Card"
