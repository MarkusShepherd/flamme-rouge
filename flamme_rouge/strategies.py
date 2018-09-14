# -*- coding: utf-8 -*-

''' strategies '''

import logging

from typing import Any, Callable, Dict, Iterable, Optional, Sequence

from .cards import Card
from .teams import Cyclist, Regular, Rouleur, Sprinteur, Team, Tuple
from .utils import input_int

LOGGER = logging.getLogger(__name__)


def _first_available(
        game: 'flamme_rouge.core.Game',
        cyclists: Iterable[Cyclist],
        key: Optional[Callable[[Cyclist], Any]] = None,
    ) -> Dict[Cyclist, 'flamme_rouge.tracks.Section']:
    available = reversed(game.track.available_start)
    cyclists = cyclists if key is None else sorted(cyclists, key=key)
    return dict(zip(cyclists, available))


class Human(Regular):
    ''' human input '''

    def __init__(self, **kwargs):
        kwargs['exhaustion'] = True
        super().__init__(**kwargs)

    def _select_cyclist(self, cyclists: Optional[Sequence[Cyclist]] = None) -> Cyclist:
        cyclists = self.cyclists if cyclists is None else cyclists

        if len(cyclists) < 2:
            return cyclists[0] if cyclists else None

        string = ', '.join(f'{cyclist} ({pos})' for pos, cyclist in enumerate(cyclists))
        prompt = f'Choose a cyclist: {string} '
        choice = input_int(prompt, lower=0, upper=len(cyclists) - 1)
        return cyclists[choice]

    def starting_position(
            self,
            game: 'flamme_rouge.core.Game',
        ) -> Tuple[Cyclist, 'flamme_rouge.tracks.Section']:
        sections = game.track.sections[:game.track.start]

        print('Currently chosen starting positions:')
        print('\n'.join(map(str, sections)))

        cyclists = [c for c in self.cyclists if c.section is None]
        cyclist = self._select_cyclist(cyclists)

        available = game.track.available_start

        lower = min(section.position for section in available)
        upper = max(section.position for section in available)

        section = None

        while section is None:
            choice = input_int(
                f'Choose position for your {cyclist}: ', lower=lower, upper=upper)
            sections = [section for section in available if section.position == choice]
            if sections:
                section = sections[0]

        return cyclist, section

    def next_cyclist(self, game: Optional['flamme_rouge.core.Game'] = None) -> Optional[Cyclist]:
        available = [cyclist for cyclist in self.cyclists if cyclist.curr_card is None]
        return self._select_cyclist(available)

    def choose_card(
            self,
            cyclist: Cyclist,
            game: Optional['flamme_rouge.core.Game'] = None,
        ) -> Optional[Card]:
        hand = sorted(cyclist.hand)
        hand_str = ', '.join(f'({i}) {c}' for i, c in enumerate(hand))
        pos = input_int(
            f'Choose your card for <{cyclist}> from hand {hand_str}: ',
            lower=0, upper=len(hand) - 1)
        return hand[pos]


class Peloton(Team):
    ''' peloton team '''

    attack_deck: Tuple[Card] = Rouleur.initial_deck + (Card.ATTACK, Card.ATTACK)
    curr_card: Optional[Card]
    _starting_positions: Optional[Dict[Cyclist, 'flamme_rouge.tracks.Section']]

    def __init__(self, name: Optional[str] = None, **kwargs):
        self.leader = Rouleur(team=self, deck=self.attack_deck)
        self.dummy = Rouleur(team=self, deck=())

        kwargs['cyclists'] = (self.leader, self.dummy)
        kwargs['exhaustion'] = False
        kwargs['order'] = 0
        kwargs['hand_size'] = 1

        super().__init__(name=name or 'Peloton', **kwargs)

        self.curr_card = None
        self._starting_positions = None

    def starting_position(
            self,
            game: 'flamme_rouge.core.Game',
        ) -> Tuple[Cyclist, 'flamme_rouge.tracks.Section']:
        if self._starting_positions is None:
            self._starting_positions = _first_available(game, self.cyclists)
        for cyclist in self.cyclists:
            if cyclist.section is None:
                return cyclist, self._starting_positions[cyclist]
        raise RuntimeError('all cyclists have been placed')

    def next_cyclist(self, game: Optional['flamme_rouge.core.Game'] = None) -> Optional[Cyclist]:
        return (
            self.leader if self.leader.curr_card is None
            else self.dummy if self.dummy.curr_card is None
            else None)

    def choose_card(
            self,
            cyclist: Cyclist,
            game: Optional['flamme_rouge.core.Game'] = None,
        ) -> Optional[Card]:
        if cyclist is self.dummy:
            card = self.curr_card
            cyclist.hand = [card]
            self.curr_card = None
            return card

        self.curr_card = super().choose_card(cyclist, game)
        return self.curr_card


class Muscle(Team):
    ''' muscle team '''

    muscle_deck = Sprinteur.initial_deck + (Card.CARD_5,)

    def __init__(self, name: Optional[str] = None, **kwargs):
        kwargs['cyclists'] = (Sprinteur(team=self, deck=self.muscle_deck), Rouleur(team=self))
        kwargs['exhaustion'] = False
        kwargs['order'] = 1
        kwargs['hand_size'] = 1

        super().__init__(name=name or 'Muscle', **kwargs)

        self._starting_positions = None

    def starting_position(
            self,
            game: 'flamme_rouge.core.Game',
        ) -> Tuple[Cyclist, 'flamme_rouge.tracks.Section']:
        if self._starting_positions is None:
            self._starting_positions = _first_available(
                game, self.cyclists, lambda x: not isinstance(x, Sprinteur))
        for cyclist in self.cyclists:
            if cyclist.section is None:
                return cyclist, self._starting_positions[cyclist]
        raise RuntimeError('all cyclists have been placed')
