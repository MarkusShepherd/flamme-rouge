#!/usr/bin/env python3
# -*- coding: utf-8 -*-

''' entry point '''

import logging
import sys

from .core import FRGame, Rouleur, Sprinteur, Strategy, Team
from .strategies import Human
from .tracks import FIRENZE_MILANO

LOGGER = logging.getLogger(__name__)

def _main():
    logging.basicConfig(
        stream=sys.stderr,
        level=logging.INFO,
        format='%(asctime)s %(levelname)-8.8s [%(name)s:%(lineno)s] %(message)s'
    )

    names = ('red', 'blue', 'green', 'black')
    teams = []
    strategy = Strategy()

    for name in names:
        sprinteur = Sprinteur()
        rouleur = Rouleur()
        team = Team(
            name=name,
            cyclists=(sprinteur, rouleur),
            strategy=Human() if name == 'blue' else strategy,
        )
        sprinteur.team = team
        rouleur.team = team
        teams.append(team)

        LOGGER.info('Team <%s> with members <%s> and <%s>', team, sprinteur, rouleur)

    game = FRGame(AVENUE_CORSO_PASEO, teams)
    game.play()

    LOGGER.info('winner: %s', game.track.leading())


if __name__ == '__main__':
    _main()
