# -*- coding: utf-8 -*-

''' actions '''

from dataclasses import dataclass


#pylint: disable=too-few-public-methods
class FRAction:
    ''' an action in Flamme Rouge '''


@dataclass(frozen=True)
class SelectStartPositionAction(FRAction):
    ''' select starting position '''

    cyclist: 'flamme_rouge.teams.Cyclist'
    position: int


@dataclass(frozen=True)
class SelectCyclistAction(FRAction):
    ''' select a cyclist to race '''

    cyclist: 'flamme_rouge.teams.Cyclist'


@dataclass(frozen=True)
class SelectCardAction(FRAction):
    ''' select a card from cyclist's hand '''

    cyclist: 'flamme_rouge.teams.Cyclist'
    card: 'flamme_rouge.cards.FRCard'
