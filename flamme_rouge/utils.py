# -*- coding: utf-8 -*-

''' util functions '''

from itertools import tee


def window(iterable, size=2):
    ''' sliding window of an iterator '''

    iterables = tee(iterable, size)

    for num, itb in enumerate(iterables):
        for _ in range(num):
            next(itb, None)

    return zip(*iterables)
