# -*- coding: utf-8 -*-

''' strategies '''

import logging

from typing import Any, Callable, Dict, Iterable, Optional, Sequence, Union

from .cards import EXHAUSTION_VALUE
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

    def __init__(self, name: str, handicap: Union[int, Sequence[int]] = 0, **kwargs):
        kwargs['exhaustion'] = True
        super().__init__(name=name, **kwargs)

        if isinstance(handicap, int):
            handicap_spinteur = handicap // 2
            handicap = (handicap_spinteur, handicap - handicap_spinteur)

        for cyclist in self.cyclists:
            cards = handicap[0] if isinstance(cyclist, Sprinteur) else handicap[1]
            cyclist.deck.extend((EXHAUSTION_VALUE,) * cards)

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

    def next_cyclist(self, game=None):
        available = [cyclist for cyclist in self.cyclists if cyclist.curr_card is None]
        return self._select_cyclist(available)

    def choose_card(self, cyclist, game=None):
        while True:
            card = input_int(f'Choose your card for <{cyclist}> from hand {cyclist.hand}: ')

            if card in cyclist.hand:
                return card


class Peloton(Team):
    ''' peloton team '''

    def __init__(self, name=None, **kwargs):
        self.leader = Rouleur(
            team=self, deck=(0, 0, 3, 3, 3, 4, 4, 4, 5, 5, 5, 6, 6, 6, 7, 7, 7), hand_size=1)
        self.dummy = Rouleur(team=self, deck=(), hand_size=1)

        kwargs['cyclists'] = (self.leader, self.dummy)
        kwargs['exhaustion'] = False
        kwargs['order'] = 0

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


class Muscle(Team):
    ''' muscle team '''

    def __init__(self, name=None, **kwargs):
        kwargs['cyclists'] = (
            Sprinteur(
                team=self,
                deck=(2, 2, 2, 3, 3, 3, 4, 4, 4, 5, 5, 5, 5, 9, 9, 9),
                hand_size=1),
            Rouleur(team=self, hand_size=1),
        )
        kwargs['exhaustion'] = False
        kwargs['order'] = 1

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
