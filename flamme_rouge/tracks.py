# -*- coding: utf-8 -*-

''' tracks '''

import logging
import re

from collections import deque

from .cards import EXHAUSTION_CARD
from .utils import class_from_path, window

LOGGER = logging.getLogger(__name__)

CLASS_REGEX = re.compile(r'[^\w.]+')


class Section:
    ''' section on the track '''

    LANE_STR_WIDTH = 20

    def __init__(self, position, lanes=2, slipstream=True, min_speed=None, max_speed=None):
        self.position = position
        self.lanes = lanes
        self.slipstream = slipstream
        self.min_speed = min_speed
        self.max_speed = max_speed

        self._cyclists = deque(maxlen=lanes)

    @property
    def cyclists(self):
        ''' cyclists '''

        return tuple(self._cyclists)

    def empty(self):
        ''' true if section is empty '''

        return not self._cyclists

    def full(self):
        ''' true if section is filled to capacity '''

        return len(self._cyclists) >= self.lanes

    def add_cyclist(self, cyclist):
        ''' add a rider to the section '''

        if self.full():
            return False
        self._cyclists.append(cyclist)
        return True

    def remove_cyclist(self, cyclist):
        ''' remove a rider from this section '''

        try:
            self._cyclists.remove(cyclist)
            return True
        except ValueError:
            pass
        return False

    def __str__(self):
        total = (self.LANE_STR_WIDTH + 1) * self.lanes - 1
        left = (total - 5) // 2
        right = total - left - 5
        top = '+' + '-' * left + f' {self.position:3d} ' + '-' * right + '+'
        if not self.slipstream:
            top += ' 🚫'

        lane_str = f' {{:{self.LANE_STR_WIDTH - 2}s}} '
        cyclists = self.cyclists
        cyclists += ('',) * (self.lanes - len(self._cyclists))
        cyclists = tuple(
            lane_str.format(str(cyclist)[:self.LANE_STR_WIDTH - 2]) for cyclist in cyclists)
        middle = '|'.join(('',) + cyclists + ('',))
        if self.max_speed is not None:
            middle = f'{middle} ≤{self.max_speed}'

        bottom = '+' + '-' * total + '+'
        if self.min_speed is not None:
            bottom = f'{bottom} ≥{self.min_speed}'

        return '\n'.join((top, middle, bottom))

class Section3(Section):
    ''' 3 lane section '''

    def __init__(self, position):
        super().__init__(position=position, lanes=3)


class Finish(Section):
    ''' finish section '''

    def __init__(self, position):
        super().__init__(position=position, slipstream=False)


class Finish3(Section):
    ''' finish section with 3 lanes '''

    def __init__(self, position):
        super().__init__(position=position, lanes=3, slipstream=False)


class MountainUp(Section):
    ''' up section '''

    def __init__(self, position):
        super().__init__(position=position, slipstream=False, max_speed=5)


class MountainDown(Section):
    ''' down section '''

    def __init__(self, position):
        super().__init__(position=position, min_speed=5)


class Supply(Section):
    ''' supply zone section '''

    def __init__(self, position):
        super().__init__(position=position, lanes=3, min_speed=4)


class Cobblestone1(Section):
    ''' cobblestone with one lane '''

    def __init__(self, position):
        super().__init__(position=position, lanes=1, slipstream=False)


class Cobblestone2(Section):
    ''' cobblestone with two lanes '''

    def __init__(self, position):
        super().__init__(position=position, slipstream=False)


class Track:
    ''' track '''

    def __init__(self, sections, start=5, finish=-5, min_players=3, max_players=4):
        self.sections = tuple(sections)
        self.start = start
        self.finish = finish if finish > 0 else len(self) + finish
        self.min_players = min_players
        self.max_players = max_players

    def __len__(self):
        return len(self.sections)

    def __iter__(self):
        return iter(self.sections)

    def cyclists(self):
        ''' generator of riders from first to last '''

        for section in reversed(self.sections):
            yield from section.cyclists

    def _move_cyclist(self, cyclist, value, start, min_speed=False):
        min_speed_value = self.sections[start].min_speed
        value = value if not min_speed or min_speed_value is None else max(value, min_speed_value)

        for i, section in enumerate(self.sections[start:start + value + 1]):
            max_speed = section.max_speed
            if max_speed is None:
                continue
            if i > max_speed:
                value = i - 1
                break
            value = min(value, max_speed)

        for pos in range(min(start + value, len(self) - 1), start, -1):
            section = self.sections[pos]
            if section.add_cyclist(cyclist):
                return pos

        return start

    def move_cyclist(self, cyclist, value, min_speed=False):
        ''' move cyclists '''

        for pos, section in enumerate(self.sections):
            if cyclist not in section.cyclists:
                continue
            end = self._move_cyclist(cyclist=cyclist, value=value, start=pos, min_speed=min_speed)
            if pos != end:
                section.remove_cyclist(cyclist)
            return end - pos

    def do_slipstream(self):
        ''' move cyclists through slipstream '''

        while True:
            for sec in window(self.sections, 3):
                if (all(s.slipstream for s in sec)
                        and sec[0].cyclists and sec[1].empty() and sec[2].cyclists):
                    for cyclist in sec[0].cyclists:
                        LOGGER.info('🚴 <%s> receives slipstream', cyclist)
                        self.move_cyclist(cyclist, 1)
                    break # start over to move cyclists at the end of the pack
            else:
                return # all slipstreams done

    def do_exhaustion(self):
        ''' add exhaustion cards '''

        for sec0, sec1 in window(self.sections[:self.finish + 1], 2):
            if sec1.empty():
                for cyclist in sec0.cyclists:
                    if not cyclist.team or cyclist.team.exhaustion:
                        LOGGER.info('🚴 <%s> gets exhausted', cyclist)
                        cyclist.discard(EXHAUSTION_CARD)

    def leading(self):
        ''' leading cyclist '''

        for section in reversed(self.sections):
            if not section.empty():
                return section.cyclists[0]

        return None

    def non_empty(self):
        ''' non-empty sections '''

        for section in self.sections:
            if not section.empty():
                yield section

    def finished(self):
        ''' game finished '''

        return any(not section.empty() for section in self.sections[self.finish:])

    def __str__(self):
        start = next(self.non_empty(), None)
        start = start.position - 1 if start is not None and start.position else 0
        finish = max(start, self.finish)
        total = (Section.LANE_STR_WIDTH + 1) * 2 + 1
        sections = self.sections[start:finish] + ('#' * total,) + self.sections[finish:]
        return '\n'.join(map(str, sections))

    @classmethod
    def from_sections(cls, sections, **kwargs):
        ''' create a track from a sequence of sections '''

        if isinstance(sections, (str, bytes)):
            return cls.from_sections(CLASS_REGEX.split(sections))

        classes = filter(None, map(class_from_path, sections))
        sections = (clazz(i) for i, clazz in enumerate(classes))
        return cls(sections=sections, **kwargs)


_SEC = (Section,)
_SEC3 = (Section3,)
_FIN = (Finish,)
_FIN3 = (Finish3,)
_UP = (MountainUp,)
_DOWN = (MountainDown,)
_SUP = (Supply,)
_COB1 = (Cobblestone1,)
_COB2 = (Cobblestone2,)

AVENUE_CORSO_PASEO = Track.from_sections(_SEC * 73 + _FIN * 5)
FIRENZE_MILANO = Track.from_sections(
    _SEC * 22 + _UP * 5 + _DOWN * 3 + _SEC * 16 + _UP * 7 + _DOWN * 3 + _SEC * 17 + _FIN * 5)
LA_HAUT_MONTAGNE = Track.from_sections(
    _SEC * 36 + _UP * 7 + _DOWN * 5 + _SEC * 14 + _UP * 12 + _FIN * 4,
    finish=-4)
PLATEAUX_DE_WALLONIE = Track.from_sections(
    _SEC * 16 + _UP * 3 + _DOWN * 3 + _SEC * 6
    + _UP * 2 + _DOWN * 2 + _SEC * 34 + _UP * 2 + _SEC * 5 + _FIN * 5,
    start=4)
STAGE_9 = Track.from_sections(
    _SEC * 12 + _SUP * 5 + _SEC * 3
    + _COB1 + _COB2 + _COB1 + _COB2 + _COB1 * 3 + _COB2 + _COB1
    + _SEC * 11 + _SUP * 5 + _SEC * 6
    + _COB1 + _COB2 + _COB1 * 4 + _COB2 + _COB1
    + _SEC * 14 + _FIN * 5,
    start=4)
