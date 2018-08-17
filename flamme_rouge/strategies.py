# -*- coding: utf-8 -*-

''' core classes '''

import logging

from .teams import Strategy
from .utils import input_int

LOGGER = logging.getLogger(__name__)


class Human(Strategy):
    ''' human input '''

    def starting_positions(self, team, game):
        sections = game.track.sections[:game.track.start]

        print('currently chosen starting positions:')
        print('\n'.join(map(str, sections)))

        result = {}

        available = [section for section in sections if not section.full()]

        lower = min(section.position for section in available)
        upper = max(section.position for section in available)

        for cyclist in team.cyclists:
            section = None

            while section is None:
                choice = input_int(
                    'Choose position for your {:s}: '.format(str(cyclist)),
                    lower=lower, upper=upper)
                sections = [section for section in available if section.position == choice]
                if sections:
                    section = sections[0]

            result[cyclist] = section
            if len(section.cyclists) + 1 >= section.lanes:
                available.remove(section)

        return result

    def next_cyclist(self, team, game=None):
        available = [cyclist for cyclist in team.cyclists if cyclist.curr_card is None]

        if len(available) < 2:
            return available[0] if available else None

        cyclists = ', '.join(
            '{:s} ({:d})'.format(str(cyclist), pos) for pos, cyclist in enumerate(available))
        prompt = 'Choose the next cyclist: {} '.format(cyclists)

        choice = input_int(prompt, lower=0, upper=len(available) - 1)

        return available[choice]

    def choose_card(self, cyclist, team=None, game=None):
        while True:
            card = input_int(
                'Choose your card for <{:s}> from hand {:s}: '.format(
                    str(cyclist), str(cyclist.hand)))

            if card in cyclist.hand:
                return card
