#!/usr/bin/env python3
# -*- coding: utf-8 -*-

''' entry point '''

import argparse
import logging
import sys

from .core import FRGame
from .strategies import Human
from .teams import Rouleur, Sprinteur, Team
from .tracks import AVENUE_CORSO_PASEO, Track
from .utils import class_from_path

LOGGER = logging.getLogger(__name__)


def _parse_args():
    parser = argparse.ArgumentParser(description='Flamme Rouge')
    parser.add_argument(
        'names', nargs='*', default=('blue', 'red', 'green', 'black'), help='names of players')
    parser.add_argument('--track', '-t', default=AVENUE_CORSO_PASEO, help='pre-defined track')
    parser.add_argument('--humans', '-H', type=int, default=1, help='number of human players')
    parser.add_argument('--verbose', '-v', action='count', default=0,
                        help='log level (repeat for more verbosity)')

    return parser.parse_args()


def _main():
    args = _parse_args()

    logging.basicConfig(
        stream=sys.stderr,
        level=logging.DEBUG if args.verbose > 0 else logging.INFO,
        format='%(levelname)-4.4s [%(name)s:%(lineno)s] %(message)s',
    )

    LOGGER.info(args)

    track = class_from_path(args.track)

    if not track:
        raise ValueError('track <{}> not found'.format(args.track))

    track = track if isinstance(track, Track) else Track.from_sections(track)
    LOGGER.info(track)

    teams = []

    for i, name in enumerate(args.names):
        sprinteur = Sprinteur()
        rouleur = Rouleur()
        team = (
            Human(name=name, cyclists=(sprinteur, rouleur)) if i < args.humans
            else Team(name=name, cyclists=(sprinteur, rouleur)))
        teams.append(team)

        LOGGER.info('Team <%s> with members <%s> and <%s>', team, sprinteur, rouleur)

    game = FRGame(track, teams)
    game.play()

    LOGGER.info('winner: %s', game.track.leading())


if __name__ == '__main__':
    _main()
