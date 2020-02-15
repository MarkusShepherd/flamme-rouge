# -*- coding: utf-8 -*-

""" core classes """

import logging

from enum import Enum, auto
from itertools import product
from random import choice, shuffle
from typing import TYPE_CHECKING, Iterable, Optional, Tuple

from .actions import (
    Action,
    RaceAction,
    SelectCardAction,
    SelectCyclistAction,
    SelectStartPositionAction,
)
from .utils import clear_list

if TYPE_CHECKING:
    # pylint: disable=cyclic-import,unused-import
    from .teams import Cyclist, Team
    from .tracks import Track

LOGGER = logging.getLogger(__name__)


class Phase(Enum):
    """ phases of a game """

    START = auto()
    RACE = auto()
    FINISH = auto()

    @property
    def next_phase(self) -> "Phase":
        """ phase after this """
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
    """ Flamme Rouge game """

    track: "Track"
    teams: Tuple["Team", ...]
    phase: Phase = Phase.START
    rounds_played: int = 0

    def __init__(self, track: "Track", teams: Iterable["Team"],) -> None:
        self.track = track
        self.reset(teams)

    def reset(self, teams: Optional[Iterable["Team"]] = None) -> "Game":
        """ reset this game """

        self.track = self.track.reset()
        teams = teams if teams is not None else self.teams
        teams = [team.reset() for team in teams]
        shuffle(teams)
        teams.sort(key=lambda team: team.order)
        self.teams = tuple(teams)
        self.phase = Phase.START
        self.rounds_played = 0

        LOGGER.debug(
            "game phase: %s; rounds: %d; finished: %s; winner: %s; active: %s",
            self.phase,
            self.rounds_played,
            self.finished,
            self.winner,
            self.active_teams,
        )

        return self

    @property
    def finished(self) -> bool:
        """ inidicates if the game is finished """
        return self.track.finished()

    @property
    def winner(self) -> Optional["Cyclist"]:
        """ winner of the game if any, else None """
        return self.track.leading if self.finished else None

    @property
    def active_teams(self) -> Tuple["Team", ...]:
        """ currently active teams """

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
            team
            for team in self.teams
            if any(c.curr_card is None for c in team.cyclists)
        )

    @property
    def sorted_teams(self) -> Tuple["Team", ...]:
        """ teams in race order """
        return tuple(clear_list(c.team for c in self.track.cyclists()))

    @property
    def cyclists(self) -> Tuple["Cyclist", ...]:
        """ all cyclists in the race """
        return tuple(c for team in self.teams for c in team.cyclists)

    def _available_actions_start(self, team: "Team") -> Tuple[Action, ...]:
        placed = frozenset(self.track.cyclists())
        cyclists = (c for c in team.cyclists if c not in placed)
        sections = self.track.available_start

        return tuple(
            SelectStartPositionAction(cyclist=c, position=s.position)
            for c, s in product(cyclists, sections)
        )

    def available_actions(self, team: "Team") -> Tuple[Action, ...]:
        """ available actions to that team """

        if team not in self.active_teams:
            return ()

        if self.phase is Phase.START:
            return self._available_actions_start(team)

        if self.phase is Phase.RACE:
            return team.available_actions

        assert self.phase is Phase.FINISH

        return ()

    def take_action(self, team: "Team", action: Action) -> Phase:
        """ a team takes an action """

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
            raise RuntimeError(f"no action available in phase <{self.phase}>")

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
            raise ValueError(f"invalid action {action}")

        if any(c.curr_card is None for c in self.cyclists):
            return

        for cyclist in self.track.cyclists():
            assert cyclist.curr_card is not None
            planned = cyclist.curr_card
            actual = self.track.move_cyclist(cyclist, cyclist.curr_card, min_speed=True)
            cyclist.curr_card = None
            LOGGER.info(
                "🚴 <%s> selected card %s and moved %d section(s)",
                cyclist,
                planned,
                actual,
            )

        self.track.do_slipstream()
        self.track.do_exhaustion()

        self.rounds_played += 1

        LOGGER.info("after %d rounds:", self.rounds_played)
        LOGGER.info(self)

    def play_action(self) -> Phase:
        """ play an action """

        teams = self.active_teams

        if not teams:
            return self.phase

        team = choice(teams)
        action = team.select_action(self)

        if action is not None:
            return self.take_action(team, action)

        return self.phase

    def play(self) -> None:
        """ play the game """

        while not self.finished:
            self.play_action()

    def __str__(self) -> str:
        return str(self.track)
