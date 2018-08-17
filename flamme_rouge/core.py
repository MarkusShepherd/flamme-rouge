# -*- coding: utf-8 -*-

''' core classes '''

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


class FRGame:
    ''' Flamme Rouge game '''

    def __init__(self, track, teams):
        self.track = track
        self.teams = list(teams)
        shuffle(self.teams)
        self.teams = tuple(self.teams)
        self.rounds_played = 0

    def starting_positions(self):
        ''' initiate the game '''

        for team in self.teams:
            for cyclist, section in team.strategy.starting_positions(team, self).items():
                section.add_cyclist(cyclist)

        LOGGER.info('starting positions:')
        LOGGER.info(self)

    def play_round(self):
        ''' play a round '''

        for team in self.teams:
            for cyclist in team.strategy.cyclists(team, self):
                cyclist.draw_hand()
                hand = tuple(cyclist.hand)
                card = team.strategy.choose_card(cyclist, team, self)
                cyclist.select_card(card)
                cyclist.discard_hand()
                LOGGER.info('cyclist <%s> received hand %s and chose <%d>', cyclist, hand, card)

        for cyclist in self.track.cyclists():
            planned = cyclist.curr_card
            actual = self.track.move_cyclist(cyclist, cyclist.curr_card)
            cyclist.curr_card = None
            LOGGER.info(
                'cyclist <%s> planned to move %d and did move %d section(s)',
                cyclist, planned, actual)

        self.track.do_slipstream()
        self.track.do_exhaustion()

        self.rounds_played += 1

        LOGGER.info('after %d rounds:', self.rounds_played)
        LOGGER.info(self)

    def play(self):
        ''' play the game '''

        self.starting_positions()

        while not self.track.finished():
            self.play_round()

    def __str__(self):
        return str(self.track)
