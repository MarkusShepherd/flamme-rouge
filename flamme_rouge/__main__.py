#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" entry point """

import argparse
import logging
import sys

from itertools import zip_longest

import inquirer

from .tracks import Track, ALL_TRACKS
from .const import COLORS
from .core import Game
from .strategies import Human, Muscle, Peloton
from .utils import class_from_path

LOGGER = logging.getLogger(__name__)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Flamme Rouge")
    parser.add_argument("names", nargs="*", help="names of players")
    parser.add_argument("--track", "-t", help="pre-defined track")
    parser.add_argument(
        "--humans", "-H", type=int, default=1, help="number of human players"
    )
    parser.add_argument(
        "--exhaustion",
        "-e",
        type=int,
        default=0,
        help="number of exhaustion cards as initial handicap",
    )
    parser.add_argument(
        "--colors",
        "-c",
        nargs="+",
        default=("blue", "red", "green", "black", "white", "magenta", "cyan", "yellow"),
        choices=COLORS,
        help="colors of the teams",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="count",
        default=0,
        help="log level (repeat for more verbosity)",
    )

    return parser.parse_args()


def main() -> None:
    """CLI entry point."""

    args = _parse_args()

    logging.basicConfig(
        stream=sys.stderr,
        level=logging.DEBUG if args.verbose > 0 else logging.INFO,
        format="%(levelname)-4.4s [%(name)s:%(lineno)s] %(message)s",
    )

    if isinstance(args.track, str) and not args.track.startswith("flamme_rouge."):
        args.track = f"flamme_rouge.{args.track}"

    LOGGER.info(args)

    track = class_from_path(args.track)

    if not track:
        tracks = [
            inquirer.questions.TaggedValue(label=t.name, value=t)
            for t in sorted(ALL_TRACKS, key=lambda t: t.name)
        ]
        question = inquirer.List(
            name="track", message="Choose a track", choices=tracks, carousel=True,
        )
        answer = inquirer.prompt([question])
        track = answer["track"]

    track = track if isinstance(track, Track) else Track.from_sections(track)
    LOGGER.info(track)

    num_players = max(track.min_players, len(args.names), args.humans)

    if num_players > track.max_players:
        LOGGER.warning(
            "you are trying to play with %d players on a track "
            "that was designed for at most %d players",
            num_players,
            track.max_players,
        )

    teams = (
        Human(name=name or f"HUM#{i}", handicap=args.exhaustion, colors=colors)
        if i < args.humans
        else Peloton(name=name or "PEL", colors=colors)
        if i == args.humans
        else Muscle(name=name or f"MUS#{i}", colors=colors)
        for i, name, colors in zip_longest(
            range(num_players), args.names, args.colors[:num_players]
        )
    )

    game = Game(track, teams)
    game.play()

    LOGGER.info("winner: %s", game.track.leading)


if __name__ == "__main__":
    main()
