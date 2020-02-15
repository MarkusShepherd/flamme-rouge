# -*- coding: utf-8 -*-

""" RL environment """

import logging
import math
import os
import sys

from collections import Counter
from collections.abc import Mapping
from enum import Enum
from functools import partial
from random import choice
from typing import Any, Iterable, List, Generator, Optional, Tuple
from dataclasses import astuple, dataclass, is_dataclass

import numpy as np

from gym.spaces import Box, Dict, Discrete, MultiBinary
from keras.models import Sequential
from keras.layers import Dense, Activation, Flatten
from keras.optimizers import Adam
from rl.agents.dqn import DQNAgent
from rl.core import Agent, Env
from rl.memory import SequentialMemory
from rl.policy import LinearAnnealedPolicy, MaxBoltzmannQPolicy  # BoltzmannQPolicy

from .actions import Action, SelectCardAction, SelectCyclistAction
from .cards import Card
from .core import Game, Phase
from .strategies import Heuristic, Muscle, Peloton  # Simple
from .teams import Cyclist, Regular, Rouleur, Sprinteur, Team
from .tracks import ALL_TRACKS, Section, Track

LOGGER = logging.getLogger(__name__)
WEIGHTS_FILE = "fr_weights.h5f"


class FRAction(Enum):
    """ enum of actions """

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

    @classmethod
    def from_action(cls, action: Action) -> Optional["FRAction"]:
        """ convert an Action to an FRAction, if possible """

        if isinstance(action, SelectCyclistAction):
            return (
                cls.CYCLIST_ROULEUR
                if isinstance(action.cyclist, Rouleur)
                else cls.CYCLIST_SPRINTEUR
                if isinstance(action.cyclist, Sprinteur)
                else None
            )

        if not isinstance(action, SelectCardAction):
            return None

        card = action.card

        for act in cls:
            if (
                isinstance(act.value, partial)
                and act.value.keywords.get("card") == card
            ):
                return act

        return None


FR_ACTIONS: Tuple[FRAction, ...] = tuple(FRAction)


def _flatten(data: Any) -> Generator:
    if is_dataclass(data):
        yield from _flatten(astuple(data))
        return

    if hasattr(data, "__iter__") and not isinstance(data, (bytes, str)):
        for item in data:
            yield from _flatten(item)
        return

    yield data


class ArrayData:
    """ array data """

    def to_array(self, dtype=float) -> np.ndarray:
        """ as data array """
        return np.array(tuple(_flatten(self)), dtype=dtype)


@dataclass
class FRSectionData(ArrayData):
    """ section data """

    lanes: int
    slipstream: bool
    min_speed: int
    max_speed: int

    @classmethod
    def from_section(cls, section: Section) -> "FRSectionData":
        """ data from section """
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
    """ own cyclist data """

    exhaustion: bool
    position: int
    lane: int
    draw_pile: Tuple[int, ...]
    hand: Tuple[int, ...]
    discard_pile: Tuple[int, ...]
    curr_card_selected: bool
    curr_card: int

    @classmethod
    def from_cyclist(cls, cyclist: Cyclist) -> "FROwnCyclistData":
        """ data from cyclist """
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
    """ other cyclist data """

    playing: bool
    exhaustion: bool
    position: int
    lane: int
    cards: Tuple[int, ...]

    @classmethod
    def from_cyclist(cls, cyclist: Optional[Cyclist]) -> "FROtherCyclistData":
        """ data from cyclist """

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
    """ complete game data """

    start: int
    finish: int
    sections: Tuple[FRSectionData, ...]
    own_cyclists: Tuple[FROwnCyclistData, ...]  # expected len: 2
    other_cyclists: Tuple[FROtherCyclistData, ...]  # expected len: 10

    @classmethod
    def from_game(cls, game: Game, team: Team) -> "FRData":
        """ data from cyclist """

        own_cyclists = sorted(
            team.sorted_cyclists,
            key=lambda c: (c.curr_card is not None, c.hand is None),
        )
        other_cyclists: List[Optional[Cyclist]] = [
            c for t in game.sorted_teams if t != team for c in t.sorted_cyclists
        ]
        other_cyclists += [None] * (10 - len(other_cyclists))

        return cls(
            start=game.track.start,
            finish=game.track.finish,
            sections=tuple(map(FRSectionData.from_section, game.track)),
            own_cyclists=tuple(map(FROwnCyclistData.from_cyclist, own_cyclists)),
            other_cyclists=tuple(map(FROtherCyclistData.from_cyclist, other_cyclists)),
        )


def _to_action(number: int, team: Team) -> Optional[Action]:
    action = FR_ACTIONS[number]

    if action in (FRAction.CYCLIST_SPRINTEUR, FRAction.CYCLIST_ROULEUR):
        ctype = action.value
        cyclist = next(
            (c for c in team.available_cyclists if isinstance(c, ctype)), None
        )
        return SelectCyclistAction(cyclist) if cyclist is not None else None

    cyclist = team.cyclist_to_select_card

    if cyclist is None:
        return None

    action = action.value(cyclist=cyclist)
    assert isinstance(action, SelectCardAction)
    return action


class AgentTeam(Regular):
    """ agent team """

    hand_size = 4

    def __init__(
        self, agent: Agent, name: Optional[str] = None, max_tries: int = 10, **kwargs,
    ) -> None:
        kwargs["hand_size"] = AgentTeam.hand_size
        super().__init__(name=name or "Agent", **kwargs)
        self.agent = agent
        self.max_tries = max_tries

    def starting_position(self, game: "Game",) -> Tuple[Cyclist, "Section"]:
        assert game.track.available_start
        cyclists = sorted(
            (c for c in self.cyclists if c.section is None),
            key=lambda c: isinstance(c, Rouleur),
        )
        assert cyclists
        return cyclists[0], game.track.available_start[-1]

    def _select_action(self, game: Game) -> Optional[Action]:
        observation = FRData.from_game(game, self).to_array()

        for _ in range(self.max_tries):
            number = self.agent.forward(observation)
            action = _to_action(number, self)
            if action in game.available_actions(self):
                return action

        LOGGER.warning("did not select an action after %d attempts", self.max_tries)

        return None

    def next_cyclist(self, game: Optional[Game] = None) -> Optional[Cyclist]:
        action = self._select_action(game) if game is not None else None
        if action is None:
            return super().next_cyclist(game)
        assert isinstance(action, SelectCyclistAction)
        return action.cyclist

    def choose_card(
        self, cyclist: Cyclist, game: Optional["Game"] = None,
    ) -> Optional[Card]:
        action = self._select_action(game) if game is not None else None
        if action is None:
            return super().choose_card(cyclist, game)
        assert isinstance(action, SelectCardAction)
        assert action.cyclist == cyclist
        return action.card


class AvailableActions(Dict):
    """ space used to restrict the available actions at each step """

    def __init__(self, nb_actions, space):
        spaces = {
            "actions": MultiBinary(nb_actions),
            "values": space,
        }
        super().__init__(spaces=spaces)
        self.shape = getattr(space, "shape", None)

    def sample(self):
        return self.spaces["values"].sample()

    def contains(self, x):
        if isinstance(x, Mapping):
            return super().contains(dict(x))
        return self.spaces["values"].contains(x)

    def __contains__(self, value):
        return self.contains(value)

    def __getattr__(self, name):
        return getattr(self.spaces["values"], name)


class FREnv(Env):
    """ Flamme Rouge Environment """

    TRACKS = tuple(track for track in ALL_TRACKS if len(track) == 78)

    game: Game
    _track: Optional[Track]
    track: Track
    opponents: Tuple[Team, ...] = (
        Peloton(colors="red"),
        Muscle(colors="green"),
        # Simple(colors='black'),
        Heuristic(colors="white"),
    )

    reward_range = (-1, len(opponents))
    action_space = Discrete(len(FRAction))
    observation_space = AvailableActions(
        nb_actions=action_space.n, space=Box(low=-1, high=77, shape=(524,)),
    )

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

    def _play_others(self) -> None:
        while True:
            teams = [team for team in self.game.active_teams if team != self.team]
            if not teams:
                return
            team = choice(teams)
            team_action = team.select_action(self.game)
            assert team_action is not None
            self.game.take_action(team, team_action)

    def reset(self) -> np.ndarray:
        self.track = self._track if self._track is not None else choice(FREnv.TRACKS)
        teams = (self.team,) + self.opponents
        self.game = Game(track=self.track, teams=teams)

        while self.game.phase is Phase.START:
            self.game.play_action()
        assert self.game.phase is Phase.RACE
        self._play_others()

        LOGGER.debug(self.game)

        return self.observation

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, dict]:
        assert not self.game.finished
        assert self.game.phase is Phase.RACE
        assert self.game.active_teams == (self.team,)

        try:
            act = _to_action(action, self.team)
            assert act is not None
            self.game.take_action(self.team, act)

        except Exception as exp:
            LOGGER.debug("encountered exception: %r", exp, exc_info=True)
            LOGGER.debug(
                "action: %d / %s / %s, available actions: %s",
                action,
                FR_ACTIONS[action],
                act,
                self.game.available_actions(self.team),
            )
            return self.observation, -1, True, {}

        if self.game.finished:
            winner = self.game.winner
            assert winner is not None
            assert winner.team is not None
            teams = self.game.sorted_teams
            assert teams[0] == winner.team
            position = teams.index(self.team) + 1
            reward = len(self.game.teams) - position
            return self.observation, reward, True, {}

        self._play_others()

        assert not self.game.finished
        assert self.game.phase is Phase.RACE
        assert self.game.active_teams == (self.team,)
        return self.observation, 0, False, {}

    def render(self, mode="human", close=False):
        print(self.game)

    def close(self):
        del self.game

    def seed(self, seed=None):
        pass

    def configure(self, *args, **kwargs):
        pass

    @property
    def observation(self):
        """ game observation """
        available = frozenset(
            filter(
                None, map(FRAction.from_action, self.game.available_actions(self.team))
            )
        )
        return {
            "actions": np.array([a in available for a in FR_ACTIONS], dtype=bool),
            "values": FRData.from_game(self.game, self.team).to_array(),
        }


class AvailableAgent(DQNAgent):
    """ agent that respects the available actions """

    logger = LOGGER

    def process_state_batch(self, batch):
        self.logger.debug("AvailableAgent.process_state_batch(%r)", batch)
        batch = [
            [
                obs.get("values", obs) if isinstance(obs, Mapping) else obs
                for obs in state
            ]
            for state in batch
        ]
        return super().process_state_batch(batch)

    def compute_q_values(self, state):
        result = super().compute_q_values(state)

        obs = state[-1]
        actions = obs.get("actions") if isinstance(obs, Mapping) else None
        if actions is not None:
            assert len(result) == len(actions)
            for i, available in enumerate(actions):
                if not available:
                    result[i] = -math.inf

        self.logger.debug("AvailableAgent.compute_q_values(%r) = %r", state, result)

        return result


def _main():
    logging.basicConfig(
        stream=sys.stderr,
        level=logging.WARNING,  # if args.verbose > 0 else logging.INFO,
        format="%(levelname)-4.4s [%(name)s:%(lineno)s] %(message)s",
    )

    nb_actions = FREnv.action_space.n
    nb_steps = 1_000_000

    model = Sequential()
    model.add(Flatten(input_shape=(1,) + FREnv.observation_space.shape))
    model.add(Dense(nb_actions * 8))
    model.add(Activation("relu"))
    # model.add(Dense(nb_actions * 4))
    # model.add(Activation('relu'))
    model.add(Dense(nb_actions * 2))
    model.add(Activation("relu"))
    model.add(Dense(nb_actions))
    model.add(Activation("linear"))
    print(model.summary())

    memory = SequentialMemory(limit=50000, window_length=1)
    policy = LinearAnnealedPolicy(
        inner_policy=MaxBoltzmannQPolicy(),
        attr="eps",
        value_max=1,
        value_min=0.05,
        value_test=0,
        nb_steps=nb_steps // 2,
    )  # BoltzmannQPolicy()
    agent = AvailableAgent(
        model=model,
        gamma=0.9999,
        nb_actions=nb_actions,
        memory=memory,
        nb_steps_warmup=50,
        target_model_update=1e-2,
        policy=policy,
        test_policy=policy,
    )
    agent.compile(Adam(lr=1e-3), metrics=["mae"])

    if os.path.isfile(WEIGHTS_FILE):
        print(f"loading pre-trained weights from {WEIGHTS_FILE}")
        agent.load_weights(WEIGHTS_FILE)

    env = FREnv(team=AgentTeam(agent=agent, colors="blue"))
    agent.fit(env, nb_steps=nb_steps, visualize=False, verbose=1)

    agent.save_weights(WEIGHTS_FILE, overwrite=True)

    agent.test(env, nb_episodes=1, visualize=True)


if __name__ == "__main__":
    _main()
