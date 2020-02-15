# -*- coding: utf-8 -*-

""" cards """

from typing import Tuple

from .utils import OrderedEnum


class Card(OrderedEnum):
    """ cards in Flamme Rouge """

    CARD_2 = (2, 2, False)
    CARD_3 = (3, 3, False)
    CARD_4 = (4, 4, False)
    CARD_5 = (5, 5, False)
    CARD_6 = (6, 6, False)
    CARD_7 = (7, 7, False)
    CARD_8 = (8, 8, False)
    CARD_9 = (9, 9, False)
    EXHAUSTION = (2, 2, True)
    ATTACK = (2, 9, False)

    def __init__(self, value_front: int, value_behind: int, exhaustion: bool) -> None:
        self.value_front = value_front
        self.value_behind = value_behind
        self.exhaustion = exhaustion

    @property
    def value_comp(self) -> Tuple[bool, int, int, bool]:
        return (
            self not in (Card.EXHAUSTION, Card.ATTACK),
            self.value_front,
            self.value_behind,
            not self.exhaustion,
        )

    def __str__(self) -> str:
        string = (
            str(self.value_front)
            if self.value_front == self.value_behind
            else f"{self.value_front}/{self.value_behind}"
        )
        return f"{string}E" if self.exhaustion else string
