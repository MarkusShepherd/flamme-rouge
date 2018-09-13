# -*- coding: utf-8 -*-

''' core classes '''

import logging

from enum import Enum, auto
from itertools import product
from random import shuffle
from typing import Iterable, Optional, Tuple

from .actions import (
    Action, RaceAction, SelectCardAction, SelectCyclistAction, SelectStartPositionAction)

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


def _execute_cyclist_action(action: SelectCyclistAction) -> None:
    cyclist = action.cyclist
    assert cyclist.curr_card is None
    assert cyclist.hand is None
    cyclist.draw_hand()
    assert cyclist.hand


def _execute_card_action(action: SelectCardAction) -> None:
    cyclist = action.cyclist
    card = action.card
    assert cyclist.curr_card is None
    assert cyclist.hand
    assert card in cyclist.hand
    cyclist.select_card(card)
    cyclist.discard_hand()


class Game:
    ''' Flamme Rouge game '''

    track: 'flamme_rouge.tracks.Track'
    teams: Tuple['flamme_rouge.teams.Team', ...]
    phase: Phase = Phase.START
    rounds_played: int = 0

    def __init__(
            self, track: 'flamme_rouge.tracks.Track', teams: Iterable['flamme_rouge.teams.Team']):
        self.track = track
        self.teams = teams
        self.reset()

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

    @property
    def finished(self) -> bool:
        ''' inidicates if the game is finished '''
        return self.track.finished()

    @property
    def winner(self) -> Optional['flamme_rouge.teams.Cyclist']:
        ''' winner of the game if any, else None '''
        return self.track.leading if self.finished else None

    @property
    def active_teams(self) -> Tuple['flamme_rouge.teams.Team', ...]:
        ''' currently active teams '''

        if self.phase is Phase.FINISH:
            return ()

        if self.phase is Phase.START:
            cyclists = frozenset(self.track.cyclists())
            for team in self.teams:
                if any(c not in cyclists for c in team.cyclists):
                    return (team,)
            return ()

        assert self.phase is Phase.RACE

        return tuple(
            team for team in self.teams if any(c.curr_card is None for c in team.cyclists))

    @property
    def cyclists(self) -> Tuple['flamme_rouge.teams.Cyclist', ...]:
        ''' all cyclists in the race '''
        return tuple(c for team in self.teams for c in team.cyclists)

    def _available_actions_start(self, team: 'flamme_rouge.teams.Team') -> Tuple[Action, ...]:
        placed = frozenset(self.track.cyclists())
        cyclists = (c for c in team.cyclists if c not in placed)
        sections = self.track.available_start

        return tuple(
            SelectStartPositionAction(c, s.position) for c, s in product(cyclists, sections))

    def available_actions(self, team: 'flamme_rouge.teams.Team') -> Tuple[Action, ...]:
        ''' available actions to that team '''

        if team not in self.active_teams:
            return ()

        if self.phase is Phase.START:
            return self._available_actions_start(team)

        if self.phase is Phase.RACE:
            return team.available_actions

        assert self.phase is Phase.FINISH

        return ()

    def take_action(self, team: 'flamme_rouge.teams.Team', action: Action) -> Phase:
        ''' a team takes an action '''

        assert team in self.active_teams
        assert action in self.available_actions(team)
        assert action.cyclist in team.cyclists

        if self.phase is Phase.START:
            assert isinstance(action, SelectStartPositionAction)
            self._execute_start_action(action)

        elif self.phase is Phase.RACE:
            assert isinstance(action, RaceAction)
            self._execute_race_action(action)

        else:
            raise RuntimeError(f'no action available in phase <{self.phase}>')

        if self.finished:
            self.phase = Phase.FINISH
        elif not self.active_teams:
            self.phase = self.phase.next_phase

        return self.phase

    def _execute_start_action(self, action: SelectStartPositionAction) -> None:
        assert 0 <= action.position < self.track.start

        section = self.track[action.position]
        assert not section.full

        section.add_cyclist(action.cyclist)

    def _execute_race_action(self, action: RaceAction) -> None:
        if isinstance(action, SelectCyclistAction):
            _execute_cyclist_action(action)
        elif isinstance(action, SelectCardAction):
            _execute_card_action(action)
        else:
            raise ValueError(f'invalid action {action}')

        if any(c.curr_card is None for c in self.cyclists):
            return

        for cyclist in self.track.cyclists():
            planned = cyclist.curr_card
            actual = self.track.move_cyclist(cyclist, cyclist.curr_card, min_speed=True)
            cyclist.curr_card = None
            LOGGER.info(
                '🚴 <%s> planned move %s and did move %d section(s)',
                cyclist, planned, actual)

        self.track.do_slipstream()
        self.track.do_exhaustion()

        self.rounds_played += 1

        LOGGER.info('after %d rounds:', self.rounds_played)
        LOGGER.info(self)

    def starting_positions(self) -> None:
        ''' initiate the game '''

        while self.phase is Phase.START:
            team = self.active_teams[0]
            cyclist, section = team.starting_position(self)
            action = SelectStartPositionAction(cyclist, section.position)
            self.take_action(team, action)

        LOGGER.info('starting positions:')
        LOGGER.info(self)

    def play_round(self) -> None:
        ''' play a round '''

        while self.active_teams:
            team = self.active_teams[0]
            for cyclist in team.order_cyclists(self):
                self.take_action(team, SelectCyclistAction(cyclist))
                hand = ', '.join(map(str, cyclist.hand))
                card = team.choose_card(cyclist, self)
                self.take_action(team, SelectCardAction(cyclist, card))
                LOGGER.info('🚴 <%s> received hand <%s> and chose <%s>', cyclist, hand, card)

    def play(self) -> None:
        ''' play the game '''

        self.starting_positions()

        while not self.finished:
            self.play_round()

    def __str__(self) -> str:
        return str(self.track)
