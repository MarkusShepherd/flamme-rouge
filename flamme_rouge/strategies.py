# -*- coding: utf-8 -*-

""" strategies """

import logging

from typing import TYPE_CHECKING, Any, Callable, Dict, Iterable, Optional, Sequence

import inquirer

from .cards import Card
from .teams import Cyclist, Regular, Rouleur, Sprinteur, Team, Tuple

if TYPE_CHECKING:
    # pylint: disable=cyclic-import,unused-import
    from .core import Game
    from .tracks import Section

LOGGER = logging.getLogger(__name__)


def _first_available(
    game: "Game",
    cyclists: Iterable[Cyclist],
    key: Optional[Callable[[Cyclist], Any]] = None,
) -> Dict[Cyclist, "Section"]:
    available = reversed(game.track.available_start)
    cyclists = cyclists if key is None else sorted(cyclists, key=key)
    return dict(zip(cyclists, available))


class Peloton(Team):
    """ peloton team """

    attack_deck: Tuple[Card, ...] = Rouleur.initial_deck + (Card.ATTACK, Card.ATTACK)
    curr_card: Optional[Card]
    _starting_positions: Optional[Dict[Cyclist, "Section"]]

    def __init__(self, **kwargs) -> None:
        self.leader = Rouleur(team=self, deck=self.attack_deck)
        self.dummy = Rouleur(team=self, deck=())

        kwargs["cyclists"] = (self.leader, self.dummy)
        kwargs["exhaustion"] = False
        kwargs["order"] = 0
        kwargs["hand_size"] = 1

        super().__init__(**kwargs)

    def reset(self) -> "Peloton":
        super().reset()
        self.curr_card = None
        self._starting_positions = None
        return self

    def starting_position(self, game: "Game",) -> Tuple[Cyclist, "Section"]:
        if self._starting_positions is None:
            self._starting_positions = _first_available(game, self.cyclists)
        for cyclist in self.cyclists:
            if cyclist.section is None:
                return cyclist, self._starting_positions[cyclist]
        raise RuntimeError("all cyclists have been placed")

    def next_cyclist(self, game: Optional["Game"] = None) -> Optional[Cyclist]:
        return (
            self.leader
            if self.leader.curr_card is None
            else self.dummy
            if self.dummy.curr_card is None
            else None
        )

    def choose_card(
        self, cyclist: Cyclist, game: Optional["Game"] = None,
    ) -> Optional[Card]:
        if cyclist is self.dummy:
            assert self.curr_card is not None
            card = self.curr_card
            cyclist.hand = [card]
            self.curr_card = None
            return card

        self.curr_card = super().choose_card(cyclist, game)
        return self.curr_card


class Muscle(Team):
    """ muscle team """

    muscle_deck: Tuple[Card, ...] = Sprinteur.initial_deck + (Card.CARD_5,)
    _starting_positions: Optional[Dict[Cyclist, "Section"]]

    def __init__(self, **kwargs) -> None:
        kwargs["cyclists"] = (
            Sprinteur(team=self, deck=self.muscle_deck),
            Rouleur(team=self),
        )
        kwargs["exhaustion"] = False
        kwargs["order"] = 1
        kwargs["hand_size"] = 1

        self._starting_positions = None

        super().__init__(**kwargs)

    def reset(self) -> "Muscle":
        super().reset()
        self._starting_positions = None
        return self

    def starting_position(self, game: "Game",) -> Tuple[Cyclist, "Section"]:
        if self._starting_positions is None:
            self._starting_positions = _first_available(
                game, self.cyclists, lambda x: not isinstance(x, Sprinteur)
            )
        for cyclist in self.cyclists:
            if cyclist.section is None:
                return cyclist, self._starting_positions[cyclist]
        raise RuntimeError("all cyclists have been placed")


class Human(Regular):
    """ human input """

    def __init__(self, **kwargs) -> None:
        kwargs["exhaustion"] = True
        super().__init__(**kwargs)

    def _select_cyclist(
        self, cyclists: Optional[Sequence[Cyclist]] = None
    ) -> Optional[Cyclist]:
        cyclists = self.cyclists if cyclists is None else cyclists

        if len(cyclists) < 2:
            return cyclists[0] if cyclists else None

        question = inquirer.List(
            name="cyclist", message="Choose a cyclist", choices=cyclists, carousel=True,
        )
        answer = inquirer.prompt([question])

        assert answer
        assert isinstance(answer.get("cyclist"), Cyclist)

        return answer["cyclist"]

    def starting_position(self, game: "Game",) -> Tuple[Cyclist, "Section"]:
        sections = game.track[: game.track.start]

        print("Currently chosen starting positions:")
        print("\n".join(map(str, sections)))

        cyclists = [c for c in self.cyclists if c.section is None]
        cyclist = self._select_cyclist(cyclists)

        assert cyclist is not None

        positions = [section.position for section in game.track.available_start]
        question = inquirer.List(
            name="position",
            message=f"Choose the position for your {cyclist}",
            choices=positions,
            default=positions[-1],
            carousel=True,
        )
        answer = inquirer.prompt([question])

        assert answer
        assert isinstance(answer.get("position"), int)

        return cyclist, game.track[answer["position"]]

    def next_cyclist(self, game: Optional["Game"] = None) -> Optional[Cyclist]:
        available = [cyclist for cyclist in self.cyclists if cyclist.curr_card is None]
        return self._select_cyclist(available)

    def choose_card(
        self, cyclist: Cyclist, game: Optional["Game"] = None,
    ) -> Optional[Card]:
        if not cyclist.hand:
            return None

        hand = sorted(set(cyclist.hand))
        hand_tags = [
            inquirer.questions.TaggedValue(label=str(c), value=c) for c in hand
        ]
        question = inquirer.List(
            name="card",
            message=f"Choose the card for your {cyclist}",
            choices=hand_tags,
            carousel=True,
        )
        answer = inquirer.prompt([question])

        assert answer
        assert isinstance(answer.get("card"), Card)

        return answer["card"]


class Simple(Regular):
    """ always go for the highest card """

    def starting_position(self, game: "Game",) -> Tuple[Cyclist, "Section"]:
        assert game.track.available_start
        cyclists = sorted(
            (c for c in self.cyclists if c.section is None),
            key=lambda c: isinstance(c, Rouleur),
        )
        assert cyclists
        return cyclists[0], game.track.available_start[-1]

    def choose_card(
        self, cyclist: Cyclist, game: Optional["Game"] = None,
    ) -> Optional[Card]:
        if not cyclist.hand:
            return None
        return sorted(cyclist.hand)[-1]


class Heuristic(Regular):
    """ try to be smart about it """

    def starting_position(self, game: "Game",) -> Tuple[Cyclist, "Section"]:
        assert game.track.available_start
        cyclists = sorted(
            (c for c in self.cyclists if c.section is None),
            key=lambda c: isinstance(c, Rouleur),
        )
        assert cyclists
        return cyclists[0], game.track.available_start[-1]

    def next_cyclist(self, game: Optional["Game"] = None) -> Optional[Cyclist]:
        cyclists = self.available_cyclists
        return (
            sorted(cyclists, key=lambda c: isinstance(c, Rouleur))[0]
            if cyclists
            else None
        )

    def choose_card(
        self, cyclist: Cyclist, game: Optional["Game"] = None,
    ) -> Optional[Card]:
        if not game:
            return super().choose_card(cyclist)

        if not cyclist.hand or not cyclist.section:
            return None

        hand = sorted(cyclist.hand)
        high_cards = cyclist.cards[-3:]
        total = sum(card.value_front for card in high_cards)
        to_go = game.track.finish - cyclist.section.position

        if to_go <= total:
            return hand[-1]

        threshold = min(card.value_front for card in high_cards)
        hand = [card for card in hand if card.value_front < threshold]

        return hand[-1] if hand else sorted(cyclist.hand)[0]
