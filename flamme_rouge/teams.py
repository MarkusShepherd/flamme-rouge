# -*- coding: utf-8 -*-

''' teams '''

import logging
import math

from random import choice, shuffle
from typing import Tuple

from termcolor import colored

from .actions import Action, SelectCardAction, SelectCyclistAction
from .const import COLORS
from .cards import EXHAUSTION_VALUE

LOGGER = logging.getLogger(__name__)


class Cyclist:
    ''' rider or cyclist '''

    initial_deck = None
    deck = None
    hand = None
    discard_pile = None
    curr_card = None

    time = 0
    finished = False

    _colors = None
    _string = None

    def __init__(self, deck=None, team=None, hand_size=4, colors=None):
        if deck is not None:
            self.initial_deck = tuple(deck)

        self.reset()

        self.team = team
        self.hand_size = hand_size or 4

        self.colors = colors

    def reset(self):
        ''' reset this cyclist '''

        self.deck = list(self.initial_deck)
        shuffle(self.deck)
        self.hand = None
        self.discard_pile = []
        self.curr_card = None
        self.time = 0
        self.finished = False
        return self

    @property
    def cards(self):
        ''' all cards of this cyclist '''

        result = self.deck + self.discard_pile
        if self.curr_card is not None:
            result.append(self.curr_card)
        return sorted(result)

    @property
    def colors(self):
        ''' print colors '''

        return self._colors

    @colors.setter
    def colors(self, value):
        self._colors = (
            {} if not value
            else COLORS.get(value.lower(), {}) if isinstance(value, str)
            else value)

    def _draw(self):
        if not self.deck:
            self.deck = self.discard_pile
            self.discard_pile = []
            shuffle(self.deck)
        return self.deck.pop(choice(range(len(self.deck)))) if self.deck else None

    def draw_hand(self, size=None):
        ''' draw a new hand '''

        size = self.hand_size if size is None else size

        self.discard_hand()
        self.hand = [card for card in (self._draw() for _ in range(size)) if card is not None]
        if not self.hand:
            self.hand = [EXHAUSTION_VALUE]

    def select_card(self, value):
        ''' select a card from hand '''

        try:
            self.hand.remove(value)
            self.curr_card = value
            return True

        except ValueError as exc:
            LOGGER.exception(exc)

        return False

    def discard(self, value):
        ''' add a card to the discard pile '''

        self.discard_pile.append(value)

    def discard_hand(self):
        ''' discard the entire hand '''

        if self.hand:
            self.discard_pile.extend(self.hand)
        self.hand = None

    def ahead_of(
            self, other: 'flamme_rouge.teams.Cyclist', track: 'flamme_rouge.tracks.Track') -> bool:
        ''' True if this cyclist is ahead of the other cyclist on the track else False '''
        return track.compare(self, other) > 0

    def __str__(self):
        if self._string is not None:
            return self._string
        string = (
            self.__class__.__name__ if self.team is None
            else f'{self.__class__.__name__} ({self.team})')
        self._string = colored(string, **self.colors) if self.colors else string
        return self._string


class Rouleur(Cyclist):
    ''' rouleur '''

    initial_deck = (3, 3, 3, 4, 4, 4, 5, 5, 5, 6, 6, 6, 7, 7, 7)


class Sprinteur(Cyclist):
    ''' sprinteur '''

    initial_deck = (2, 2, 2, 3, 3, 3, 4, 4, 4, 5, 5, 5, 9, 9, 9)


class Team:
    ''' team '''

    def __init__(self, name, cyclists, exhaustion=True, order=math.inf, colors=None):
        self.name = name
        self.cyclists = tuple(cyclists)
        self.exhaustion = exhaustion
        self.order = order
        self.colors = colors or {}

        for cyclist in self.cyclists:
            cyclist.team = self
            cyclist.colors = cyclist.colors or self.colors

    @property
    def available_actions(self) -> Tuple[Action]:
        ''' available actions '''

        cyclists = [c for c in self.cyclists if c.curr_card is None]

        if not cyclists:
            return ()

        cyclists_drawn = [c for c in cyclists if c.hand is not None]

        if cyclists_drawn:
            assert len(cyclists_drawn) == 1
            cyclist = cyclists_drawn[0]
            return tuple(SelectCardAction(cyclist, card) for card in cyclist.hand)

        return tuple(map(SelectCyclistAction, cyclists))

    def starting_positions(self, game):
        ''' select starting positions '''

        result = {}

        available = [
            section for section in game.track.sections[:game.track.start] if not section.full]

        for cyclist in self.cyclists:
            section = choice(available)
            result[cyclist] = section
            if len(section.cyclists) + 1 >= section.lanes:
                available.remove(section)

        return result

    def available_cyclists(self):
        ''' available cyclist this round '''

        return [
            cyclist for cyclist in self.cyclists
            if not cyclist.finished and cyclist.curr_card is None]

    #pylint: disable=unused-argument
    def next_cyclist(self, game=None):
        ''' select the next cyclist '''

        available = self.available_cyclists()
        return choice(available) if available else None

    def order_cyclists(self, game=None):
        ''' generator of cyclists in order '''

        while True:
            cyclist = self.next_cyclist(game)
            if cyclist is None:
                return
            LOGGER.debug(
                '🚴 hand: %r; deck: %r; pile: %r',
                cyclist.hand, cyclist.deck, cyclist.discard_pile)
            yield cyclist

    #pylint: disable=no-self-use,unused-argument
    def choose_card(self, cyclist, game=None):
        ''' choose card '''

        return choice(cyclist.hand) if cyclist.hand else None

    def reset(self):
        ''' reset this team '''

        for cyclist in self.cyclists:
            cyclist.reset()
        return self

    def __str__(self):
        return self.name

class Regular(Team):
    ''' team with rouleur and sprinteur '''

    def __init__(self, hand_size=None, **kwargs):
        kwargs['cyclists'] = (
            Sprinteur(team=self, hand_size=hand_size),
            Rouleur(team=self, hand_size=hand_size),
        )
        super().__init__(**kwargs)
