# -*- coding: utf-8 -*-

''' RL environment '''

import logging
import sys

from collections import Counter
from dataclasses import astuple, dataclass, is_dataclass
from enum import Enum
from functools import partial
from random import choice
from typing import Any, Iterable, Generator, Optional, Tuple

import numpy as np

from gym.spaces import Box, Discrete
from keras.models import Sequential
from keras.layers import Dense, Activation, Flatten
from keras.optimizers import Adam
from rl.agents.dqn import DQNAgent
from rl.core import Agent, Env
from rl.memory import SequentialMemory
from rl.policy import BoltzmannQPolicy

from .actions import Action, SelectCardAction, SelectCyclistAction
from .cards import Card
from .core import Game, Phase
from .strategies import Muscle, Peloton
from .teams import Cyclist, Regular, Rouleur, Sprinteur, Team
from .tracks import ALL_TRACKS, Section, Track

LOGGER = logging.getLogger(__name__)


class FRAction(Enum):
    ''' enum of actions '''
    CYCLIST_ROULEUR = Rouleur
    CYCLIST_SPRINTEUR = Sprinteur
    SELECT_2 = partial(SelectCardAction, card=Card.CARD_2)
    SELECT_3 = partial(SelectCardAction, card=Card.CARD_3)
    SELECT_4 = partial(SelectCardAction, card=Card.CARD_4)
    SELECT_5 = partial(SelectCardAction, card=Card.CARD_5)
    SELECT_6 = partial(SelectCardAction, card=Card.CARD_6)
    SELECT_7 = partial(SelectCardAction, card=Card.CARD_7)
    SELECT_8 = partial(SelectCardAction, card=Card.CARD_8)
    SELECT_9 = partial(SelectCardAction, card=Card.CARD_9)
    SELECT_EXHAUSTION = partial(SelectCardAction, card=Card.EXHAUSTION)
    SELECT_ATTACK = partial(SelectCardAction, card=Card.ATTACK)

FR_ACTIONS: Tuple[FRAction, ...] = tuple(FRAction)


def _flatten(data: Any) -> Generator:
    if is_dataclass(data):
        yield from _flatten(astuple(data))
        return

    if hasattr(data, '__iter__') and not isinstance(data, (bytes, str)):
        for item in data:
            yield from _flatten(item)
        return

    yield data


class ArrayData:
    ''' array data '''
    def to_array(self, dtype=float) -> np.ndarray:
        ''' as data array '''
        return np.array(tuple(_flatten(self)), dtype=dtype)


@dataclass
class FRSectionData(ArrayData):
    ''' section data '''

    lanes: int
    slipstream: bool
    min_speed: int
    max_speed: int

    @classmethod
    def from_section(cls, section: Section) -> 'FRSectionData':
        ''' data from section '''
        return cls(
            lanes=section.lanes,
            slipstream=section.slipstream,
            min_speed=section.min_speed or 0,
            max_speed=section.max_speed or 9,
        )


def _count_cards(cards: Iterable[Card]) -> Tuple[int, ...]:
    counter = Counter(cards)
    return tuple(counter[card] for card in Card)


@dataclass
class FROwnCyclistData(ArrayData):
    ''' own cyclist data '''

    exhaustion: bool
    position: int
    lane: int
    draw_pile: Tuple[int, ...]
    hand: Tuple[int, ...]
    discard_pile: Tuple[int, ...]
    curr_card_selected: bool
    curr_card: int

    @classmethod
    def from_cyclist(cls, cyclist: Cyclist) -> 'FROwnCyclistData':
        ''' data from cyclist '''
        assert cyclist.team is not None
        assert cyclist.section is not None
        lane = cyclist.section.lane(cyclist)
        assert lane is not None

        return cls(
            exhaustion=cyclist.team.exhaustion,
            position=cyclist.section.position,
            lane=lane,
            draw_pile=_count_cards(cyclist.deck),
            hand=_count_cards(cyclist.hand or ()),
            discard_pile=_count_cards(cyclist.discard_pile or ()),
            curr_card_selected=cyclist.curr_card is not None,
            curr_card=0 if cyclist.curr_card is None else cyclist.curr_card.value_front,
        )


@dataclass
class FROtherCyclistData(ArrayData):
    ''' other cyclist data '''

    playing: bool
    exhaustion: bool
    position: int
    lane: int
    cards: Tuple[int, ...]

    @classmethod
    def from_cyclist(cls, cyclist: Optional[Cyclist]) -> 'FROtherCyclistData':
        ''' data from cyclist '''

        if cyclist is None:
            return cls(
                playing=False,
                exhaustion=False,
                position=-1,
                lane=-1,
                cards=_count_cards(()),
            )

        assert cyclist.team is not None
        assert cyclist.section is not None
        lane = cyclist.section.lane(cyclist)
        assert lane is not None

        return cls(
            playing=True,
            exhaustion=cyclist.team.exhaustion,
            position=cyclist.section.position,
            lane=lane,
            cards=_count_cards(cyclist.cards),
        )


@dataclass(frozen=True)
class FRData(ArrayData):
    ''' complete game data '''

    start: int
    finish: int
    sections: Tuple[FRSectionData, ...]
    own_cyclists: Tuple[FROwnCyclistData, FROwnCyclistData]
    other_cyclists: Tuple[
        FROtherCyclistData, FROtherCyclistData,
        FROtherCyclistData, FROtherCyclistData,
        FROtherCyclistData, FROtherCyclistData,
        FROtherCyclistData, FROtherCyclistData,
        FROtherCyclistData, FROtherCyclistData]

    @classmethod
    def from_game(cls, game: Game, team: Team) -> 'FRData':
        ''' data from cyclist '''

        own_cyclists = sorted(
            team.sorted_cyclists, key=lambda c: (c.curr_card is not None, c.hand is None))
        other_cyclists = [c for t in game.sorted_teams if t != team for c in t.sorted_cyclists]
        other_cyclists += [None] * (10 - len(other_cyclists))

        return cls(
            start=game.track.start,
            finish=game.track.finish,
            sections=tuple(map(FRSectionData.from_section, game.track)),
            own_cyclists=tuple(map(FROwnCyclistData.from_cyclist, own_cyclists)),
            other_cyclists=tuple(map(FROtherCyclistData.from_cyclist, other_cyclists)),
        )


# class FRPolicy(BoltzmannQPolicy):
#     ''' policy '''

#     def select_action(
#             self,
#             q_values: np.ndarray,
#             available_actions: Optional[Iterable[int]] = None,
#         ) -> int:
#         if available_actions is None:
#             return super().select_action(q_values)

#         available_actions = frozenset(available_actions)

#         assert available_actions

#         if len(available_actions) == 1:
#             return next(iter(available_actions))

#         assert q_values.ndim == 1
#         q_values = q_values.astype('float64')
#         nb_actions = q_values.shape[0]
#         assert min(available_actions) >= 0
#         assert max(available_actions) < nb_actions

#         exp_values = np.exp(np.clip(q_values / self.tau, self.clip[0], self.clip[1]))
#         for i in range(nb_actions):
#             if i not in available_actions:
#                 exp_values[i] = 0
#         total = np.sum(exp_values)
#         assert total > 0
#         probs = exp_values / np.sum(exp_values)
#         action = np.random.choice(range(nb_actions), p=probs)
#         return action


# class FRAgent(DQNAgent):
#     ''' agent '''

#     game: Optional[Game] = None

#     def __init__(self, **kwargs) -> None:
#         policy = FRPolicy()
#         kwargs['policy'] = policy
#         kwargs['test_policy'] = policy
#         super().__init__(**kwargs)


#     def forward(self, observation: Any) -> int:
#         if available_actions is None:
#             return super().forward(observation)

#         state = self.memory.get_recent_state(observation)
#         q_values = self.compute_q_values(state)
#         if self.training:
#             action = self.policy.select_action(
#                 q_values=q_values, available_actions=available_actions)
#         else:
#             action = self.test_policy.select_action(
#                 q_values=q_values, available_actions=available_actions)

#         self.recent_observation = observation
#         self.recent_action = action

#         return action


def _to_action(number: int, team: Team) -> Action:
    action = FR_ACTIONS[number]

    LOGGER.debug('_to_action(%d, %r) = %r', number, team, action)

    if action in (FRAction.CYCLIST_SPRINTEUR, FRAction.CYCLIST_ROULEUR):
        ctype = action.value
        cyclist = next(c for c in team.available_cyclists if isinstance(c, ctype))
        return SelectCyclistAction(cyclist)

    cyclist = team.cyclist_to_select_card
    assert cyclist is not None
    action = action.value(cyclist=cyclist)
    assert isinstance(action, SelectCardAction)
    return action


class AgentTeam(Regular):
    ''' agent team '''

    def __init__(
            self,
            agent: Agent,
            name: Optional[str] = None,
            max_tries: int = 10,
            **kwargs,
        ) -> None:
        super().__init__(name=name or 'Agent', **kwargs)
        self.agent = agent
        self.max_tries = max_tries

    def starting_position(
            self,
            game: 'Game',
        ) -> Tuple[Cyclist, 'Section']:
        assert game.track.available_start
        cyclists = sorted(
            (c for c in self.cyclists if c.section is None), key=lambda c: isinstance(c, Rouleur))
        assert cyclists
        return cyclists[0], game.track.available_start[-1]

    def _select_action(self, game: Game) -> Optional[Action]:
        observation = FRData.from_game(game, self).to_array()

        for _ in range(self.max_tries):
            number = self.agent.forward(observation)
            action = _to_action(number, self)
            if action in game.available_actions(self):
                return action

        LOGGER.warning('did not select an action after %d attempts', self.max_tries)

        return None

    def next_cyclist(self, game: Optional[Game] = None) -> Optional[Cyclist]:
        action = self._select_action(game) if game is not None else None
        if action is None:
            return super().next_cyclist(game)
        assert isinstance(action, SelectCyclistAction)
        return action.cyclist

    def choose_card(
            self,
            cyclist: Cyclist,
            game: Optional['Game'] = None,
        ) -> Optional[Card]:
        action = self._select_action(game) if game is not None else None
        if action is None:
            return super().choose_card(cyclist, game)
        assert isinstance(action, SelectCardAction)
        assert action.cyclist == cyclist
        return action.card


class FREnv(Env):
    ''' Flamme Rouge Environment '''

    TRACKS = tuple(track for track in ALL_TRACKS if len(track) == 78)

    reward_range = (0, 1)
    action_space = Discrete(len(FRAction))
    observation_space = Box(low=0, high=77, shape=(524,))

    game: Game
    _track: Optional[Track]
    track: Track
    opponents: Tuple[Team, ...] = (Peloton(), Muscle())

    def __init__(
            self,
            team: Team,
            opponents: Optional[Tuple[Team, ...]] = None,
            track: Optional[Track] = None,
        ) -> None:
        super().__init__()
        self.team = team
        self.opponents = opponents or self.opponents
        self._track = track

    def reset(self) -> np.ndarray:
        self.track = self._track if self._track is not None else choice(FREnv.TRACKS)
        teams = (self.team,) + self.opponents
        self.game = Game(track=self.track, teams=teams)
        self.game.reset()

        while self.game.phase is not Phase.RACE or self.game.active_teams != (self.team,):
            available_teams = [t for t in self.game.active_teams if t != self.team]
            assert available_teams
            team = available_teams[0]
            action = self.team.select_action(self.game)
            self.game.take_action(team, action)

        return self.observation

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, dict]:
        assert not self.game.finished
        assert self.game.phase is Phase.RACE
        assert self.game.active_teams == (self.team,)

        act = _to_action(action, self.team)

        try:
            self.game.take_action(self.team, act)

        except Exception as exp:
            LOGGER.exception(exp)
            return self.observation, -1000, True, {}

        if self.game.finished:
            winner = self.game.winner
            assert winner is not None
            assert winner.team is not None
            return self.observation, winner.team == self.team, True, {}

        while True:
            teams = [team for team in self.game.active_teams if team != self.team]

            if not teams:
                break

            team = choice(teams)
            team_action = team.select_action(self.game)
            assert team_action is not None
            self.game.take_action(team, team_action)

        assert not self.game.finished
        assert self.game.phase is Phase.RACE
        assert self.game.active_teams == (self.team,)
        return self.observation, 0, False, {}

    def render(self, mode='human', close=False):
        print(self.game)

    def close(self):
        del self.game

    def seed(self, seed=None):
        pass

    def configure(self, *args, **kwargs):
        pass

    @property
    def observation(self):
        ''' game observation '''
        return FRData.from_game(self.game, self.team).to_array()


def _main():
    logging.basicConfig(
        stream=sys.stderr,
        level=logging.DEBUG, # if args.verbose > 0 else logging.INFO,
        format='%(levelname)-4.4s [%(name)s:%(lineno)s] %(message)s',
    )

    nb_actions = FREnv.action_space.n

    model = Sequential()
    model.add(Flatten(input_shape=(1,) + FREnv.observation_space.shape))
    model.add(Dense(64))
    model.add(Activation('relu'))
    model.add(Dense(32))
    model.add(Activation('relu'))
    model.add(Dense(16))
    model.add(Activation('relu'))
    model.add(Dense(nb_actions))
    model.add(Activation('linear'))
    print(model.summary())

    memory = SequentialMemory(limit=50000, window_length=1)
    policy = BoltzmannQPolicy()
    agent = DQNAgent(
        model=model, nb_actions=nb_actions, memory=memory, nb_steps_warmup=10,
        target_model_update=1e-2, policy=policy, test_policy=policy)
    agent.compile(Adam(lr=1e-3), metrics=['mae'])

    env = FREnv(team=AgentTeam(agent=agent))
    agent.fit(env, nb_steps=50000, visualize=False, verbose=2)

    agent.save_weights('fr_weights.h5f', overwrite=True)

    agent.test(env, nb_episodes=5, visualize=True)


if __name__ == '__main__':
    _main()
