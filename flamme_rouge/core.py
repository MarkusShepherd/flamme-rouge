# -*- coding: utf-8 -*-

''' core classes '''

import logging

from enum import Enum, auto
from itertools import product
from random import shuffle
from typing import Dict, Iterable, Optional, Tuple

from .actions import Action, SelectStartPositionAction

LOGGER = logging.getLogger(__name__)


class Phase(Enum):
    ''' phases of a game '''

    START = auto()
    RACE = auto()
    FINISH = auto()

    @property
    def next_phase(self) -> 'Phase':
        ''' phase after this '''
        return Phase(self.value + 1)


class Game:
    ''' Flamme Rouge game '''

    rounds_played: int = 0
    phase: Phase = Phase.START
    _actions: Dict['flamme_rouge.teams.Team', Action]

    def __init__(
            self, track: 'flamme_rouge.tracks.Track', teams: Iterable['flamme_rouge.teams.Team']):
        self.track = track
        self.teams = teams
        self.reset()

    @property
    def finished(self) -> bool:
        ''' inidicates if the game is finished '''
        return self.track.finished()

    @property
    def winner(self) -> Optional['flamme_rouge.teams.Cyclist']:
        ''' winner of the game if any, else None '''
        return self.track.leading if self.finished else None

    @property
    def active_teams(self) -> Tuple['flamme_rouge.teams.Team']:
        ''' currently active teams '''
        if self.phase is Phase.FINISH:
            return ()

        if self.phase is Phase.START:
            cyclists = frozenset(self.track.cyclists())
            for team in self.teams:
                if any(c not in cyclists for c in team.cyclists):
                    return (team,)
            raise RuntimeError('phase is START, but all cyclists have been placed')

        assert self.phase is Phase.RACE

        return tuple(
            team for team in self.teams if any(c.curr_card is None for c in team.cyclists))

    def _available_actions_start(self, team: 'flamme_rouge.teams.Team') -> Tuple[Action]:
        placed = frozenset(self.track.cyclists())
        cyclists = (c for c in team.cyclists if c not in placed)
        sections = self.track.available_start

        return tuple(
            SelectStartPositionAction(c, s.position) for c, s in product(cyclists, sections))

    def available_actions(self, team: 'flamme_rouge.teams.Team') -> Tuple[Action]:
        ''' available actions to that team '''

        if team not in self.active_teams:
            return ()

        if self.phase is Phase.START:
            return self._available_actions_start(team)

        if self.phase is Phase.RACE:
            return team.available_actions

        assert self.phase is Phase.FINISH

        return ()

    def reset(self) -> 'Game':
        ''' reset this game '''

        self.track = self.track.reset()
        teams = [team.reset() for team in self.teams]
        shuffle(teams)
        teams.sort(key=lambda team: team.order)
        self.teams = tuple(teams)
        self.phase = Phase.START
        self.rounds_played = 0
        return self

    def starting_positions(self) -> None:
        ''' initiate the game '''

        for team in self.teams:
            for cyclist, section in team.starting_positions(self).items():
                section.add_cyclist(cyclist)

        LOGGER.info('starting positions:')
        LOGGER.info(self)

    def play_round(self) -> None:
        ''' play a round '''

        for team in self.teams:
            for cyclist in team.order_cyclists(self):
                cyclist.draw_hand()
                hand = tuple(cyclist.hand)
                card = team.choose_card(cyclist, self)
                cyclist.select_card(card)
                cyclist.discard_hand()
                LOGGER.info('🚴 <%s> received hand %s and chose <%d>', cyclist, hand, card)

        for cyclist in self.track.cyclists():
            planned = cyclist.curr_card
            actual = self.track.move_cyclist(cyclist, cyclist.curr_card, min_speed=True)
            cyclist.curr_card = None
            LOGGER.info(
                '🚴 <%s> planned to move %d and did move %d section(s)',
                cyclist, planned, actual)

        self.track.do_slipstream()
        self.track.do_exhaustion()

        self.rounds_played += 1

        LOGGER.info('after %d rounds:', self.rounds_played)
        LOGGER.info(self)

    def play(self) -> None:
        ''' play the game '''

        self.starting_positions()

        while not self.track.finished():
            self.play_round()

    def __str__(self) -> str:
        return str(self.track)
