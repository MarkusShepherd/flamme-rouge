#!/usr/bin/env python3

''' core classes '''

from collections import deque
from random import choice, shuffle


class Section:
    ''' section on the track '''

    def __init__(self, position, lanes=2, slipstream=True, min_speed=None, max_speed=None):
        self.position = position
        self.lanes = lanes
        self.slipstream = slipstream
        self.min_speed = min_speed
        self.max_speed = max_speed

        self._riders = deque(maxlen=lanes)

    def empty(self):
        ''' true if section is empty '''

        return not self._riders

    def full(self):
        ''' true if section is filled to capacity '''

        return len(self._riders) >= self.lanes

    def add_rider(self, rider):
        ''' add a rider to the section '''

        if self.full():
            return False
        self._riders.append(rider)
        return True

    # def remove_rider(self, rider):
    #     pass


class Rider:
    ''' rider or cyclist '''

    hand = None

    def __init__(self, deck):
        self.deck = list(deck)
        shuffle(self.deck)
        self.discard_pile = []
        self.draw_hand()

    def _draw(self):
        if not self.deck:
            self.deck = self.discard_pile
            self.discard_pile = []
            shuffle(self.deck)
        return self.deck.pop(choice(range(len(self.deck))))

    def draw_hand(self, size=4):
        ''' draw a new hand '''

        self.discard_hand()
        self.hand = [self._draw() for _ in range(size)]

    def select_card(self, value):
        ''' select a card from hand '''

        return self.hand.remove(value)

    def discard(self, value):
        ''' add a card to the discard pile '''

        self.discard_pile.append(value)

    def discard_hand(self):
        ''' discard the entire hand '''

        if self.hand:
            self.discard_pile.extend(self.hand)
        self.hand = None


class Rouleur(Rider):
    ''' rouleur '''

    def __init__(self):
        super().__init__(deck=(3, 3, 3, 4, 4, 4, 5, 5, 5, 6, 6, 6, 7, 7, 7))


class Sprinteur(Rider):
    ''' sprinteur '''

    def __init__(self):
        super().__init__(deck=(2, 2, 2, 3, 3, 3, 4, 4, 4, 5, 5, 5, 9, 9, 9))
