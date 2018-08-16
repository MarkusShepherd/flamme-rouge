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


def parse_int(string, base=10):
    ''' safely convert an object to int if possible, else return None '''

    if isinstance(string, int):
        return string

    try:
        return int(string, base=base)

    except Exception:
        pass

    try:
        return int(string)

    except Exception:
        pass

    return None

def input_int(prompt, base=10, lower=None, upper=None):
    ''' prompt for an integer input until valid '''

    while True:
        value = parse_int(input(prompt), base)

        if value is None:
            continue

        if lower is not None and value < lower:
            continue

        if upper is not None and value > upper:
            continue

        break

    return value
