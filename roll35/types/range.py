# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

from __future__ import annotations

from collections.abc import Container, Sequence
from typing import Any, TypeGuard, cast

from .item import Cost

_RangeMember = Cost
RangeMember = _RangeMember | None


def israngemember(v: Any, /) -> TypeGuard[_RangeMember]:
    return isinstance(v, int) or isinstance(v, float)


class R35Range(Container):
    '''A mutable range-like object that supports both ints and floats.

       Used by roll35.data to ranges of costs.

       THe read only properties min and max track the lowest and highest
       values added to the range, and are initialized based on the list
       of values passed to the constructor.'''
    MIN_VALUE = float('-inf')
    MAX_VALUE = float('inf')

    def __init__(self: R35Range, /, values: Sequence[RangeMember] | R35Range = []) -> None:
        self._min: RangeMember = None
        self._max: RangeMember = None
        self._empty = True

        if not values:
            pass
        elif isinstance(values, self.__class__):
            self._min = values._min
            self._max = values._max
            self._empty = values._empty
        else:
            v = [x for x in cast(Sequence[RangeMember], values) if israngemember(x)]

            if v:
                self._min = min(cast(Sequence[_RangeMember], values))
                self._max = max(cast(Sequence[_RangeMember], values))
                self._empty = False
            else:
                self._min = None
                self._max = None
                self._empty = True

    def __repr__(self: R35Range, /) -> str:
        return f'R35Range({self.min}, {self.max}, empty={self._empty})'

    def __contains__(self: R35Range, v: Any, /) -> bool:
        if self._empty:
            return False
        elif israngemember(v):
            return self.min <= v <= self.max
        elif isinstance(v, R35Range):
            return v.min in self and v.max in self
        elif v == 'varies':
            return self.min <= 0 <= self.max
        else:
            raise ValueError(f'{type(v)} is not supported by R35Range objects.')

    @classmethod
    def _rangecheck(cls, v: RangeMember, /) -> bool:
        if v is None:
            return False

        return cls.MIN_VALUE <= v <= cls.MAX_VALUE

    def add(self: R35Range, v: Sequence[R35Range | RangeMember], /) -> None:
        '''Add a sequence of values to the range.'''
        for e in v:
            match e:
                case e if e is None:
                    pass
                case R35Range(min=minv, max=maxv):
                    if self._min is None or self._max is None:
                        self._min = minv
                        self._max = maxv
                        self._empty = False
                    else:
                        self._min = min(minv, self._min)
                        self._max = max(maxv, self._max)
                case e if israngemember(e):
                    if self._rangecheck(e):
                        if self._min is None or self._max is None:
                            self._min = e
                            self._max = e
                            self._empty = False
                        else:
                            self._min = min(e, self._min)
                            self._max = max(e, self._max)
                    else:
                        raise ValueError(f'{e} is out of range for R35Range objects.')
                case e:
                    raise TypeError(f'{type(e)} is not supported by R35Range objects.')

    def reset(self: R35Range, /) -> None:
        '''Reset the cost range to the default values.'''
        self._min = None
        self._max = None
        self._empty = True

    def overlaps(self: R35Range, other: R35Range, /) -> bool:
        '''Return true if this cost range overlaps with other.'''
        if not isinstance(other, R35Range):
            raise ValueError('Must specify a R35Range object.')

        return (self.min in other) or (self.max in other) or (other.min in self) or (other.max in self)

    @property
    def min(self: R35Range, /) -> _RangeMember:
        '''The lowest value that has been added to the range.'''
        if self._min is None:
            return self.MIN_VALUE
        else:
            return self._min

    @property
    def max(self: R35Range, /) -> _RangeMember:
        '''The highest value that has been added to the range.'''
        if self._max is None:
            return self.MAX_VALUE
        else:
            return self._max
