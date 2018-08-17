# -*- coding: utf-8 -*-

''' core classes '''

import logging

from random import shuffle

LOGGER = logging.getLogger(__name__)


class FRGame:
    ''' Flamme Rouge game '''

    def __init__(self, track, teams):
        self.track = track
        self.teams = list(teams)
        shuffle(self.teams)
        self.teams = tuple(self.teams)
        self.rounds_played = 0

    def starting_positions(self):
        ''' initiate the game '''

        for team in self.teams:
            for cyclist, section in team.starting_positions(self).items():
                section.add_cyclist(cyclist)

        LOGGER.info('starting positions:')
        LOGGER.info(self)

    def play_round(self):
        ''' play a round '''

        for team in self.teams:
            for cyclist in team.order_cyclists(self):
                cyclist.draw_hand()
                hand = tuple(cyclist.hand)
                card = team.choose_card(cyclist, self)
                cyclist.select_card(card)
                cyclist.discard_hand()
                LOGGER.info('cyclist <%s> received hand %s and chose <%d>', cyclist, hand, card)

        for cyclist in self.track.cyclists():
            planned = cyclist.curr_card
            actual = self.track.move_cyclist(cyclist, cyclist.curr_card)
            cyclist.curr_card = None
            LOGGER.info(
                'cyclist <%s> planned to move %d and did move %d section(s)',
                cyclist, planned, actual)

        self.track.do_slipstream()
        self.track.do_exhaustion()

        self.rounds_played += 1

        LOGGER.info('after %d rounds:', self.rounds_played)
        LOGGER.info(self)

    def play(self):
        ''' play the game '''

        self.starting_positions()

        while not self.track.finished():
            self.play_round()

    def __str__(self):
        return str(self.track)
