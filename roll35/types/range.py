# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

import collections.abc


class R35Range(collections.abc.Container):
    '''A mutable range-like object that supports both ints and floats.

       Used by roll35.data to ranges of costs.

       THe read only properties min and max track the lowest and highest
       values added to the range, and are initialized based on the list
       of values passed to the constructor.'''
    MIN_VALUE = float('-inf')
    MAX_VALUE = float('inf')

    def __init__(self, values=[]):
        if not values:
            self._min = None
            self._max = None
            self._empty = True
        elif isinstance(values, self.__class__):
            self._min = values.min
            self._max = values.max
            self._empty = False
        elif values and all(map(self._typecheck, values)):
            self._min = min(values)
            self._max = max(values)
            self._empty = False
        else:
            raise ValueError('Unsupported type for initializing R35Range.')

    def __repr__(self):
        return f'R35Range({ self.min }, { self.max }, empty={ self._empty })'

    def __contains__(self, v):
        if self._empty:
            return False
        elif self._typecheck(v):
            return self._min <= v <= self._max
        elif isinstance(v, R35Range):
            return v.min in self and v.max in self
        else:
            raise ValueError(f'{ type(v) } is not supported by R35Range objects.')

    @staticmethod
    def _typecheck(v):
        return isinstance(v, int) or isinstance(v, float)

    @classmethod
    def _rangecheck(cls, v):
        return cls.MIN_VALUE <= v <= cls.MAX_VALUE

    @staticmethod
    def valid(v):
        '''Check if a given value is a valid as a member of a R35Range object.'''
        if R35Range._typecheck(v):
            return R35Range._rangecheck(v)
        else:
            return False

    def add(self, *v):
        '''Add values to the range.'''
        for e in v:
            match e:
                case R35Range(min=minv, max=maxv):
                    if self._empty:
                        self._min = minv
                        self._max = maxv
                        self._empty = False
                    else:
                        self._min = min(minv, self._min)
                        self._max = max(maxv, self._max)
                case e if self._typecheck(e):
                    if self._rangecheck(e):
                        if self._empty:
                            self._min = e
                            self._max = e
                            self._empty = False
                        else:
                            self._min = min(e, self._min)
                            self._max = max(e, self._max)
                    else:
                        raise ValueError(f'{ e } is out of range for R35Range objects.')
                case e:
                    raise TypeError(f'{ type(e) } is not supported by R35Range objects.')

    def reset(self):
        '''Reset the cost range to the default values.'''
        self._min = None
        self._max = None
        self._empty = True

    def overlaps(self, other):
        '''Return true if this cost range overlaps with other.'''
        if not isinstance(other, R35Range):
            raise ValueError('Must specify a R35Range object.')

        return (self.min in other) or (self.max in other) or (other.min in self) or (other.max in self)

    @property
    def min(self):
        if self._empty:
            return self.MIN_VALUE
        else:
            return self._min

    @property
    def max(self):
        if self._empty:
            return self.MAX_VALUE
        else:
            return self._max
