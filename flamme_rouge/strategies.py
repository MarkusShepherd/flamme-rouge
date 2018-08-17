# -*- coding: utf-8 -*-

''' core classes '''

import logging

from random import shuffle

from .cards import EXHAUSTION_CARD
from .teams import Regular, Rouleur, Sprinteur, Team
from .utils import input_int

LOGGER = logging.getLogger(__name__)


def _available_start(game):
    sections = game.track.sections[:game.track.start]
    return [section for section in sections if not section.full()]


def _first_available(game, cyclists, key=None):
    available = reversed(_available_start(game))
    cyclists = cyclists if key is None else sorted(cyclists, key=key)
    return dict(zip(cyclists, available))


class Human(Regular):
    ''' human input '''

    def __init__(self, name, handicap=0):
        super().__init__(name=name, exhaustion=True)

        if isinstance(handicap, int):
            handicap_spinteur = handicap // 2
            handicap = (handicap_spinteur, handicap - handicap_spinteur)

        for cyclist in self.cyclists:
            cards = handicap[0] if isinstance(cyclist, Sprinteur) else handicap[1]
            cyclist.deck.extend((EXHAUSTION_CARD,) * cards)

    def starting_positions(self, game):
        sections = game.track.sections[:game.track.start]

        print('currently chosen starting positions:')
        print('\n'.join(map(str, sections)))

        result = {}

        available = _available_start(game)

        lower = min(section.position for section in available)
        upper = max(section.position for section in available)

        for cyclist in self.cyclists:
            section = None

            while section is None:
                choice = input_int(
                    'Choose position for your {:s}: '.format(str(cyclist)),
                    lower=lower, upper=upper)
                sections = [section for section in available if section.position == choice]
                if sections:
                    section = sections[0]

            result[cyclist] = section
            if len(section.cyclists) + 1 >= section.lanes:
                available.remove(section)

        return result

    def next_cyclist(self, game=None):
        available = [cyclist for cyclist in self.cyclists if cyclist.curr_card is None]

        if len(available) < 2:
            return available[0] if available else None

        cyclists = ', '.join(
            '{:s} ({:d})'.format(str(cyclist), pos) for pos, cyclist in enumerate(available))
        prompt = 'Choose the next cyclist: {} '.format(cyclists)

        choice = input_int(prompt, lower=0, upper=len(available) - 1)

        return available[choice]

    def choose_card(self, cyclist, game=None):
        while True:
            card = input_int(
                'Choose your card for <{:s}> from hand {:s}: '.format(
                    str(cyclist), str(cyclist.hand)))

            if card in cyclist.hand:
                return card


class Peloton(Team):
    ''' peloton team '''

    def __init__(self, name=None):
        self.leader = Rouleur(self)
        self.dummy = Rouleur(self)
        super().__init__(
            name=name or 'Peloton', cyclists=(self.leader, self.dummy), exhaustion=False, order=0)

        self.leader.deck.extend((0, 0))
        shuffle(self.leader.deck)
        self.dummy.deck = []

        self.curr_card = None

    def starting_positions(self, game):
        return _first_available(game, self.cyclists)

    def next_cyclist(self, game=None):
        return (
            self.leader if self.leader.curr_card is None
            else self.dummy if self.dummy.curr_card is None
            else None)

    def choose_card(self, cyclist, game=None):
        if cyclist is self.dummy:
            card = self.curr_card
            cyclist.hand = [card]
            self.curr_card = None
            return card

        card = super().choose_card(cyclist, game)

        if card:
            self.curr_card = card
            return card

        assert game

        # discard Attack! card
        cyclist.hand.remove(0)

        first = None
        for cyc in game.track.cyclists():
            if cyc in self.cyclists:
                first = cyc
                break
        assert first

        card = 2 if cyclist is first else 9
        cyclist.hand.append(card)
        self.curr_card = 11 - card
        return card


class Muscle(Regular):
    ''' muscle team '''

    def __init__(self, name=None):
        super().__init__(name=name or 'Muscle', exhaustion=False, order=1)

        for cyclist in self.cyclists:
            if isinstance(cyclist, Sprinteur):
                cyclist.deck.append(5)

    def starting_positions(self, game):
        return _first_available(game, self.cyclists, lambda x: not isinstance(x, Sprinteur))
