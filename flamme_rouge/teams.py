# -*- coding: utf-8 -*-

""" teams """

import logging
import math

from random import choice, shuffle
from typing import (
    TYPE_CHECKING,
    Dict,
    Generator,
    List,
    Iterable,
    Optional,
    Sequence,
    Tuple,
    Union,
    cast,
)

from termcolor import colored

from .actions import (
    Action,
    SelectCardAction,
    SelectCyclistAction,
    SelectStartPositionAction,
)
from .const import COLORS
from .core import Phase
from .cards import Card

if TYPE_CHECKING:
    # pylint: disable=cyclic-import,unused-import
    from .core import Game
    from .tracks import Section, Track

LOGGER = logging.getLogger(__name__)
Color = Union[Dict[str, str], str, None]


class Cyclist:
    """ rider or cyclist """

    initial_deck: Tuple[Card, ...]
    handicap: Optional[int]
    deck: List[Card]
    hand: Optional[List[Card]]
    discard_pile: List[Card]
    curr_card: Optional[Card]
    section: Optional["Section"]

    time: int = 0
    finished: bool = False

    _colors: Dict[str, str]
    _string: Optional[str] = None

    def __init__(
        self,
        deck: Optional[Iterable[Card]] = None,
        team: Optional["Team"] = None,
        hand_size: int = 4,
        colors: Color = None,
        handicap: Optional[int] = None,
    ) -> None:
        if deck is not None:
            self.initial_deck = tuple(deck)
        self.handicap = handicap

        self.team = team
        self.hand_size = hand_size or 4

        self.colors = colors

        self.reset()

    def reset(self) -> "Cyclist":
        """ reset this cyclist """

        handicap = self.handicap or 0
        self.deck = list(self.initial_deck) + [Card.EXHAUSTION] * handicap
        shuffle(self.deck)
        self.hand = None
        self.discard_pile = []
        self.curr_card = None
        self.section = None
        self.time = 0
        self.finished = False

        LOGGER.debug(
            "%s - deck: %s, hand: %s, hand size: %d, card: %s, discard: %s, "
            "handicap: %d, section: %s, time: %d, finished: %s",
            self,
            ", ".join(map(str, self.deck)),
            self.hand,
            self.hand_size,
            self.curr_card,
            self.discard_pile,
            handicap,
            self.section,
            self.time,
            self.finished,
        )

        self._string = None

        return self

    @property
    def cards(self) -> Tuple[Card, ...]:
        """ all cards of this cyclist """
        result = self.deck + self.discard_pile
        if self.hand is not None:
            result.extend(self.hand)
        if self.curr_card is not None:
            result.append(self.curr_card)
        return tuple(sorted(result))

    @property
    def colors(self) -> Dict[str, str]:
        """ print colors """
        return self._colors

    @colors.setter
    def colors(self, value: Color):
        self._colors = (
            {}
            if not value
            else COLORS.get(value.lower(), {})
            if isinstance(value, str)
            else value
        )

    def _draw(self) -> Optional[Card]:
        if not self.deck:
            self.deck = self.discard_pile
            self.discard_pile = []
            shuffle(self.deck)
        return self.deck.pop(choice(range(len(self.deck)))) if self.deck else None

    def draw_hand(self, size: Optional[int] = None) -> None:
        """ draw a new hand """

        size = self.hand_size if size is None else size

        self.discard_hand()
        self.hand = [
            card for card in (self._draw() for _ in range(size)) if card is not None
        ]
        if not self.hand:
            self.hand = [Card.EXHAUSTION]

    def select_card(self, card: Card) -> bool:
        """ select a card from hand """

        assert self.hand is not None

        try:
            self.hand.remove(card)
            self.curr_card = card
            return True

        except ValueError as exc:
            LOGGER.exception(exc)

        return False

    def discard(self, card: Card) -> None:
        """ add a card to the discard pile """
        self.discard_pile.append(card)

    def discard_hand(self) -> None:
        """ discard the entire hand """
        if self.hand:
            self.discard_pile.extend(self.hand)
        self.hand = None

    def ahead_of(self, other: "Cyclist", track: "Track",) -> bool:
        """ True if this cyclist is ahead of the other cyclist on the track else False """
        return track.compare(self, other) > 0

    def __str__(self) -> str:
        if self._string is not None:
            return self._string
        string = (
            self.__class__.__name__
            if self.team is None
            else f"{self.__class__.__name__} ({self.team})"
        )
        self._string = colored(string, **self.colors) if self.colors else string
        return self._string


class Rouleur(Cyclist):
    """ rouleur """

    initial_deck = (Card.CARD_3, Card.CARD_4, Card.CARD_5, Card.CARD_6, Card.CARD_7) * 3


class Sprinteur(Cyclist):
    """ sprinteur """

    initial_deck = (Card.CARD_2, Card.CARD_3, Card.CARD_4, Card.CARD_5, Card.CARD_9) * 3


class Team:
    """ team """

    def __init__(
        self,
        cyclists: Iterable[Cyclist],
        name: Optional[str] = None,
        exhaustion: bool = True,
        order: float = math.inf,
        colors: Color = None,
        handicap: Union[int, Sequence[int]] = 0,
        hand_size: Optional[int] = None,
    ) -> None:
        self.name = name or self.__class__.__name__
        self.cyclists = tuple(cyclists)
        self.exhaustion = exhaustion
        self.order = order
        self.colors = colors or {}

        if isinstance(handicap, int):
            value, extra = divmod(handicap, len(self.cyclists))
            self.handicap = (value + 1,) * extra + (value,) * (
                len(self.cyclists) - extra
            )
        else:
            self.handicap = tuple(handicap)

        assert len(self.handicap) == len(self.cyclists)

        for cyclist, h_cap in zip(self.cyclists, self.handicap):
            cyclist.team = self
            cyclist.colors = cast(Dict[str, str], cyclist.colors or self.colors)
            cyclist.handicap = h_cap if cyclist.handicap is None else cyclist.handicap
            cyclist.hand_size = (
                hand_size if hand_size is not None else cyclist.hand_size
            )

        self.reset()

    @property
    def available_cyclists(self) -> Tuple[Cyclist, ...]:
        """ available cyclist this round """
        return tuple(c for c in self.cyclists if not c.finished and c.curr_card is None)

    @property
    def sorted_cyclists(self) -> Tuple[Cyclist, ...]:
        """ cyclists in race order """
        return tuple(
            sorted(
                self.cyclists,
                key=lambda c: (-math.inf, -math.inf, isinstance(c, Rouleur))
                if c.section is None
                else (c.section.position, c.section.lane(c), isinstance(c, Rouleur)),
            )
        )

    @property
    def need_to_select_cyclist(self) -> bool:
        """ time to select a cyclist """
        return all(c.hand is None for c in self.available_cyclists)

    @property
    def need_to_select_card(self) -> bool:
        """ time to select a card """
        return any(c.hand is not None for c in self.available_cyclists)

    @property
    def cyclist_to_select_card(self) -> Optional[Cyclist]:
        """ the cyclist to select a card from hand, if any """
        cyclists = [c for c in self.available_cyclists if c.hand is not None]
        assert len(cyclists) <= 1
        return cyclists[0] if cyclists else None

    @property
    def available_actions(self) -> Tuple[Action, ...]:
        """ available actions """

        if self.need_to_select_cyclist:
            return tuple(map(SelectCyclistAction, self.available_cyclists))

        if not self.need_to_select_card:
            return ()

        cyclist = self.cyclist_to_select_card
        assert cyclist is not None
        assert cyclist.hand is not None
        return tuple(SelectCardAction(cyclist, card) for card in cyclist.hand)

    def select_action(self, game: "Game") -> Optional[Action]:
        """ select the next action """

        if game.phase is Phase.FINISH:
            return None

        cyclist: Optional[Cyclist]

        if game.phase is Phase.START:
            cyclist, section = self.starting_position(game)
            return SelectStartPositionAction(cyclist, section.position)

        assert game.phase is Phase.RACE

        if self.need_to_select_cyclist:
            cyclist = self.next_cyclist(game)
            assert cyclist is not None
            return SelectCyclistAction(cyclist)

        cyclist = self.cyclist_to_select_card

        if cyclist is not None:
            cards = ", ".join(map(str, cyclist.cards))
            hand = ", ".join(map(str, sorted(cyclist.hand or ())))
            card = self.choose_card(cyclist, game)
            assert card is not None
            LOGGER.debug(
                "🚴 <%s> has cards <%s>, received hand <%s> and selected card <%s>",
                cyclist,
                cards,
                hand,
                card,
            )
            return SelectCardAction(cyclist, card)

        return None

    def starting_position(self, game: "Game",) -> Tuple[Cyclist, "Section"]:
        """ select starting positions """

        cyclists = [c for c in self.cyclists if c.section is None]
        assert cyclists
        return choice(cyclists), choice(game.track.available_start)

    # pylint: disable=unused-argument
    def next_cyclist(self, game: Optional["Game"] = None) -> Optional[Cyclist]:
        """ select the next cyclist """

        available = self.available_cyclists
        return choice(available) if available else None

    def order_cyclists(
        self, game: Optional["Game"] = None,
    ) -> Generator[Cyclist, None, None]:
        """ generator of cyclists in order """
        while True:
            cyclist = self.next_cyclist(game)
            if cyclist is None:
                return
            LOGGER.debug(
                "🚴 hand: %r; deck: %r; pile: %r",
                cyclist.hand,
                cyclist.deck,
                cyclist.discard_pile,
            )
            yield cyclist

    # pylint: disable=no-self-use,unused-argument
    def choose_card(
        self, cyclist: Cyclist, game: Optional["Game"] = None,
    ) -> Optional[Card]:
        """ choose card """
        return choice(cyclist.hand) if cyclist.hand else None

    def reset(self) -> "Team":
        """ reset this team """
        for cyclist in self.cyclists:
            cyclist.reset()
        LOGGER.debug("team <%s> reset", self)
        return self

    def __str__(self) -> str:
        return getattr(self, "name", None) or self.__class__.__name__


class Regular(Team):
    """ team with rouleur and sprinteur """

    def __init__(self, **kwargs) -> None:
        kwargs["cyclists"] = (Rouleur(team=self), Sprinteur(team=self))
        super().__init__(**kwargs)
