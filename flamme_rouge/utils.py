# -*- coding: utf-8 -*-

""" util functions """

import logging

from collections import OrderedDict
from enum import Enum
from functools import lru_cache
from importlib import import_module
from itertools import tee
from typing import Any, Iterable, List, Optional, Tuple, TypeVar

LOGGER = logging.getLogger(__name__)

Typed = TypeVar("Typed")


def clear_list(items: Iterable[Optional[Typed]]) -> List[Typed]:
    """ return unique items in order of first ocurrence """
    return list(OrderedDict.fromkeys(i for i in items if i is not None))


def window(iterable: Iterable[Typed], size: int = 2) -> Iterable[Tuple[Typed, ...]]:
    """ sliding window of an iterator """

    iterables = tee(iterable, size)

    for num, itb in enumerate(iterables):
        for _ in range(num):
            next(itb, None)

    return zip(*iterables)


def parse_int(string: Any, base: int = 10) -> Optional[int]:
    """ safely convert an object to int if possible, else return None """

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


def input_int(
    prompt: str,
    base: int = 10,
    lower: Optional[int] = None,
    upper: Optional[int] = None,
) -> int:
    """ prompt for an integer input until valid """

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


@lru_cache(maxsize=128)
def class_from_path(path: Any) -> Any:
    """ load an object from the dotted path """

    if not isinstance(path, str):
        return path

    parts = path.split(".")

    try:
        if len(parts) == 1:
            return globals().get(path) or import_module(path)

        obj = import_module(parts[0])

        for part in parts[1:]:
            if not obj:
                break
            obj = getattr(obj, part, None)

        return obj

    except ImportError as exc:
        LOGGER.exception(exc)

    return None


class OrderedEnum(Enum):
    """ ordered enum """

    @property
    def value_comp(self) -> Any:
        """ the value used for comparison """
        return self.value

    # pylint: disable=comparison-with-callable
    def __ge__(self, other: Any) -> bool:
        if self.__class__ is other.__class__:
            return self.value_comp >= other.value_comp
        return NotImplemented

    def __gt__(self, other: Any) -> bool:
        if self.__class__ is other.__class__:
            return self.value_comp > other.value_comp
        return NotImplemented

    def __le__(self, other: Any) -> bool:
        if self.__class__ is other.__class__:
            return self.value_comp <= other.value_comp
        return NotImplemented

    def __lt__(self, other: Any) -> bool:
        if self.__class__ is other.__class__:
            return self.value_comp < other.value_comp
        return NotImplemented
