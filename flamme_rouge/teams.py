# -*- coding: utf-8 -*-

''' teams '''

import logging
import math

from random import choice, shuffle
from typing import Optional, Tuple

from termcolor import colored

from .actions import Action, SelectCardAction, SelectCyclistAction, SelectStartPositionAction
from .const import COLORS
from .core import Phase
from .cards import EXHAUSTION_VALUE

LOGGER = logging.getLogger(__name__)


class Cyclist:
    ''' rider or cyclist '''

    initial_deck = None
    deck = None
    hand = None
    discard_pile = None
    curr_card = None
    section: Optional['flamme_rouge.tracks.Section']

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
        self.section = None
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
    def available_cyclists(self) -> Tuple[Cyclist, ...]:
        ''' available cyclist this round '''

        return tuple(c for c in self.cyclists if not c.finished and c.curr_card is None)

    @property
    def need_to_select_cyclist(self) -> bool:
        ''' time to select a cyclist '''
        return all(c.hand is None for c in self.available_cyclists)

    @property
    def need_to_select_card(self) -> bool:
        ''' time to select a card '''
        return any(c.hand is not None for c in self.available_cyclists)

    @property
    def cyclist_to_select_card(self) -> Optional[Cyclist]:
        ''' the cyclist to select a card from hand, if any '''
        cyclists = [c for c in self.available_cyclists if c.hand is not None]
        assert len(cyclists) <= 1
        return cyclists[0] if cyclists else None

    @property
    def available_actions(self) -> Tuple[Action, ...]:
        ''' available actions '''

        if self.need_to_select_cyclist:
            return tuple(map(SelectCyclistAction, self.available_cyclists))

        if not self.need_to_select_card:
            return ()

        cyclist = self.cyclist_to_select_card
        assert cyclist is not None
        return tuple(SelectCardAction(cyclist, card) for card in cyclist.hand)

    def select_action(self, game: 'flamme_rouge.core.Game') -> Optional[Action]:
        ''' select the next action '''

        if game.phase is Phase.FINISH:
            return None

        if game.phase is Phase.START:
            cyclist, section = self.starting_position(game)
            return SelectStartPositionAction(cyclist, section.position)

        assert game.phase is Phase.RACE

        # actions = self.available_actions
        # if not actions:
        #     return None
        # if len(actions) == 1:
        #     return actions[0]

        if self.need_to_select_cyclist:
            return SelectCyclistAction(self.next_cyclist(game))

        cyclist = self.cyclist_to_select_card

        if cyclist is not None:
            card = self.choose_card(cyclist, game)
            return SelectCardAction(cyclist, card)

        return None

    def starting_position(
            self,
            game: 'flamme_rouge.core.Game',
        ) -> Tuple[Cyclist, 'flamme_rouge.tracks.Section']:
        ''' select starting positions '''

        cyclists = [c for c in self.cyclists if c.section is None]
        assert cyclists
        return choice(cyclists), choice(game.track.available_start)

    #pylint: disable=unused-argument
    def next_cyclist(self, game: Optional['flamme_rouge.core.Game'] = None) -> Optional[Cyclist]:
        ''' select the next cyclist '''

        available = self.available_cyclists
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
