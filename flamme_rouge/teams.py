# -*- coding: utf-8 -*-

''' teams '''

import logging

from random import choice, shuffle

from .cards import EXHAUSTION_CARD

LOGGER = logging.getLogger(__name__)


class Cyclist:
    ''' rider or cyclist '''

    hand = None
    curr_card = None

    def __init__(self, deck, team=None):
        self.deck = list(deck)
        shuffle(self.deck)
        self.discard_pile = []
        self.team = team

    def _draw(self):
        if not self.deck:
            self.deck = self.discard_pile
            self.discard_pile = []
            shuffle(self.deck)
        return self.deck.pop(choice(range(len(self.deck)))) if self.deck else None

    def draw_hand(self, size=4):
        ''' draw a new hand '''

        self.discard_hand()
        self.hand = list(filter(None, (self._draw() for _ in range(size))))
        if not self.hand:
            self.hand = [EXHAUSTION_CARD]

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

    def __str__(self):
        if self.team is None:
            return self.__class__.__name__
        return '{:s} ({:s})'.format(self.__class__.__name__, str(self.team))


class Rouleur(Cyclist):
    ''' rouleur '''

    def __init__(self):
        super().__init__(deck=(3, 3, 3, 4, 4, 4, 5, 5, 5, 6, 6, 6, 7, 7, 7))


class Sprinteur(Cyclist):
    ''' sprinteur '''

    def __init__(self):
        super().__init__(deck=(2, 2, 2, 3, 3, 3, 4, 4, 4, 5, 5, 5, 9, 9, 9))


class Team:
    ''' team '''

    def __init__(self, name, cyclists, strategy=None):
        self.name = name
        self.cyclists = tuple(cyclists)
        self.strategy = strategy if strategy is not None else Strategy()

    def __str__(self):
        return self.name


class Strategy:
    ''' strategy '''

    #pylint: disable=no-self-use
    def starting_positions(self, team, game):
        ''' select starting positions '''

        result = {}

        available = [
            section for section in game.track.sections[:game.track.start] if not section.full()]

        for cyclist in team.cyclists:
            section = choice(available)
            result[cyclist] = section
            if len(section.cyclists) + 1 >= section.lanes:
                available.remove(section)

        return result

    #pylint: disable=no-self-use,unused-argument
    def next_cyclist(self, team, game=None):
        ''' select the next cyclist '''

        available = [cyclist for cyclist in team.cyclists if cyclist.curr_card is None]
        return choice(available) if available else None

    def cyclists(self, team, game=None):
        ''' generator of cyclists in order '''

        while True:
            cyclist = self.next_cyclist(team, game)
            if cyclist is None:
                return
            yield cyclist

    #pylint: disable=no-self-use,unused-argument
    def choose_card(self, cyclist, team=None, game=None):
        ''' choose card '''

        return choice(cyclist.hand) if cyclist.hand else None
