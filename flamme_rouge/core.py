# -*- coding: utf-8 -*-

''' core classes '''

import logging

from collections import deque
from random import choice, shuffle

from .utils import window

LOGGER = logging.getLogger(__name__)

EXHAUSTION_CARD = 2


class Section:
    ''' section on the track '''

    LANE_STR_WIDTH = 20

    def __init__(self, position, lanes=2, slipstream=True, min_speed=None, max_speed=None):
        self.position = position
        self.lanes = lanes
        self.slipstream = slipstream
        self.min_speed = min_speed
        self.max_speed = max_speed

        self._cyclists = deque(maxlen=lanes)

    @property
    def cyclists(self):
        ''' cyclists '''

        return tuple(self._cyclists)

    def empty(self):
        ''' true if section is empty '''

        return not self._cyclists

    def full(self):
        ''' true if section is filled to capacity '''

        return len(self._cyclists) >= self.lanes

    def add_cyclist(self, cyclist):
        ''' add a rider to the section '''

        if self.full():
            return False
        self._cyclists.append(cyclist)
        return True

    def remove_cyclist(self, cyclist):
        ''' remove a rider from this section '''

        try:
            self._cyclists.remove(cyclist)
            return True
        except ValueError:
            pass
        return False

    def __str__(self):
        total = (self.LANE_STR_WIDTH + 1) * self.lanes - 1
        left = (total - 5) // 2
        right = total - left - 5
        top = '+' + '-' * left + ' {:3d} '.format(self.position) + '-' * right + '+'
        if self.slipstream:
            top += ' S'

        lane_str = ' {{:{:d}s}} '.format(self.LANE_STR_WIDTH - 2)
        cyclists = self.cyclists
        cyclists += ('',) * (self.lanes - len(self._cyclists))
        cyclists = tuple(
            lane_str.format(str(cyclist)[:self.LANE_STR_WIDTH - 2]) for cyclist in cyclists)
        middle = '|'.join(('',) + cyclists + ('',))
        if self.min_speed is not None:
            middle = '{:s} ≤{:d}'.format(middle, self.min_speed)

        bottom = '+' + '-' * total + '+'
        if self.max_speed is not None:
            bottom = '{:s} ≥{:d}'.format(bottom, self.max_speed)

        return '\n'.join((top, middle, bottom))


class Track:
    ''' track '''

    def __init__(self, sections, start=4, finish=-5):
        self.sections = tuple(sections)
        self.start = start
        self.finish = finish if finish > 0 else len(self) + finish

    def __len__(self):
        return len(self.sections)

    def __iter__(self):
        return iter(self.sections)

    def cyclists(self):
        ''' generator of riders from first to last '''

        for section in reversed(self.sections):
            yield from section.cyclists

    def _move_cyclist(self, cyclist, value, start):
        min_speed = self.sections[start].min_speed
        value = value if min_speed is None else max(value, min_speed)

        for i, section in enumerate(self.sections[start:start + value + 1]):
            max_speed = section.max_speed
            if max_speed is None:
                continue
            if i > max_speed:
                value = i - 1
                break
            value = min(value, max_speed)

        for pos in range(min(start + value, len(self) - 1), start, -1):
            section = self.sections[pos]
            if section.add_cyclist(cyclist):
                return pos

        return start

    def move_cyclist(self, cyclist, value):
        ''' move cyclists '''

        for pos, section in enumerate(self.sections):
            if cyclist not in section.cyclists:
                continue
            end = self._move_cyclist(cyclist, value, pos)
            if pos != end:
                section.remove_cyclist(cyclist)
            return end - pos

    def do_slipstream(self):
        ''' move cyclists through slipstream '''

        while True:
            for sec in window(self.sections, 3):
                if (all(s.slipstream for s in sec)
                        and sec[0].cyclists and sec[1].empty() and sec[2].cyclists):
                    for cyclist in sec[0].cyclists:
                        LOGGER.info('cyclist <%s> receives slipstream', cyclist)
                        self.move_cyclist(cyclist, 1)
                    break # start over to move cyclists at the end of the pack
            else:
                return # all slipstreams done

    def do_exhaustion(self):
        ''' add exhaustion cards '''

        for sec0, sec1 in window(self.sections, 2):
            if sec1.empty():
                for cyclist in sec0.cyclists:
                    LOGGER.info('cyclist <%s> gets exhausted', cyclist)
                    cyclist.discard(EXHAUSTION_CARD)

    def leading(self):
        ''' leading cyclist '''

        for section in reversed(self.sections):
            if not section.empty():
                return section.cyclists[0]

        return None

    def finished(self):
        ''' game finished '''

        return any(not section.empty() for section in self.sections[self.finish:])

    def __str__(self):
        return '\n'.join(map(str, self.sections))


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
