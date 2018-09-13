# -*- coding: utf-8 -*-

''' actions '''

from dataclasses import dataclass


#pylint: disable=too-few-public-methods
@dataclass(frozen=True)
class Action:
    ''' an action in Flamme Rouge '''
    cyclist: 'flamme_rouge.teams.Cyclist'


@dataclass(frozen=True)
class SelectStartPositionAction(Action):
    ''' select starting position '''
    position: int


@dataclass(frozen=True)
class RaceAction(Action):
    ''' an action during the race phase '''


@dataclass(frozen=True)
class SelectCyclistAction(RaceAction):
    ''' select a cyclist to race '''


@dataclass(frozen=True)
class SelectCardAction(RaceAction):
    ''' select a card from cyclist's hand '''
    card: 'flamme_rouge.cards.Card'
