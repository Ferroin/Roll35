# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

'''Data type definitons.'''

import abc
import collections.abc

CATEGORY = [
    'armor',
    'weapon',
    'potion',
    'ring',
    'rod',
    'scroll',
    'staff',
    'wand',
    'wondrous',
]

RANK = [
    'minor',
    'medium',
    'major',
]

LIMITED_RANK = [
    'medium',
    'major',
]

SUBRANK = [
    'lesser',
    'greater',
]

SLOTLESS_SUBRANK = [
    'least',
    'lesser',
    'greater',
]

SLOT = [
    'belt',
    'body',
    'chest',
    'eyes',
    'feet',
    'hands',
    'head',
    'headband',
    'neck',
    'shoulders',
    'wrists',
    'slotless',
]


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
            return v >= self._min and v <= self._max
        elif isinstance(v, R35Range):
            return v.min in self and v.max in self
        else:
            raise ValueError(f'{ type(v) } is not supported by R35Range objects.')

    @staticmethod
    def _typecheck(v):
        return isinstance(v, int) or isinstance(v, float)

    @classmethod
    def _rangecheck(cls, v):
        return v >= cls.MIN_VALUE and v <= cls.MAX_VALUE

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


class R35Container(abc.ABC, collections.abc.Collection):
    '''Base class used by R35Map and R35List.

       This exists just to minimize code duplication.'''
    def __init__(self):
        self._costs = R35Range()

    def __len__(self):
        return len(self._data)

    def __iter__(self):
        return self._data.__iter__()

    def __contains__(self, key):
        return key in self._data

    @property
    def costs(self):
        return self._costs

    @staticmethod
    def _get_costs(item):
        match item:
            case R35Container(costs=R35Range()):
                item.sync()
                return (item.costs.min, item.costs.max)
            case {'value': {'costrange': [low, high]}} if R35Range.valid(low) and R35Range.valid(high):
                return (low, high)
            case {'costrange': [low, high]} if R35Range.valid(low) and R35Range.valid(high):
                return (low, high)
            case {'value': {'cost': cost}} if R35Range.valid(cost):
                return (cost, cost)
            case {'cost': cost} if R35Range.valid(cost):
                return (cost, cost)
            case _:
                return None

    def sync(self):
        '''Recompute the costs for this container.'''
        self._recompute_costs()

    @abc.abstractmethod
    def _recompute_costs(self):
        return NotImplemented


class R35Map(R35Container, collections.abc.MutableMapping):
    '''A simple cost-tracking mapping class.

       In addition to the standard mapping protocol, this class also
       provides equivalents to the `dict.items()`, `dict.values()`, and
       `dict.keys()` methods, allowing it to be used almost transparently
       as a dictionary.

       It also maintains a property called costs, which is a
       roll35.types.R35Range object that tracks the minimum and maximum
       cost of items that have been added to the mapping.

       Costs are only updated for contained items that are one of:
       - Another roll35.types.R35Container.
       - A mapping with a key called 'cost' that has a value that is
         either an integer or a float.
       - A mapping with a key called 'costrange' that has a value which
         is an list with two values, one for the minimum cost and one
         for the maximum cost.

       Keys must be strings or integers.

       This class is (intentionally) optimized for WORM access
       patterns. In-place replacement of existing keys is expensive
       as it requires rescanning the contained items to recompute the
       `costs` property.'''
    def __init__(self, data=None):
        super().__init__()
        self._data = dict()

        if data:
            for k, v in data.items():
                self[k] = v

    def __repr__(self):
        return f'R35Map({ self.cost }, { self._data })'

    def __getitem__(self, key):
        if key in self._data:
            return self._data[key]
        else:
            raise KeyError(key)

    def __setitem__(self, key, value):
        if not (isinstance(key, str) or isinstance(key, int)):
            raise KeyError('Only string and integer keys are supported by R35Map objects.')

        match self._get_costs(value):
            case None:
                if key in self:
                    del self[key]

                self._data[key] = value
            case (cost_min, cost_max):
                if key in self:
                    del self[key]

                self._data[key] = value
                self._costs.add(cost_min)
                self._costs.add(cost_max)

    def __delitem__(self, key):
        if key in self._data:
            del self._data[key]

            self._recompute_costs()
        else:
            raise KeyError(key)

    def _recompute_costs(self):
        self._costs.reset()

        for item in self._data.values():
            match self._get_costs(item):
                case None:
                    pass
                case (cost_min, cost_max):
                    self._costs.add(cost_min)
                    self._costs.add(cost_max)

    def items(self):
        return self._data.items()

    def keys(self):
        return self._data.keys()

    def values(self):
        return self._data.values()


class R35List(R35Container, collections.abc.MutableSequence):
    '''A simple cost-tracking list class.

       It also maintains a property called costs, which is a
       roll35.types.R35Range object that tracks the minimum and maximum
       cost of items that have been added to the mapping.

       Costs are only updated for contained items that are one of:
       - Another roll35.types.R35Container.
       - A mapping with a key called 'cost' that has a value that is
         either an integer or a float.
       - A mapping with a key called 'costrange' that has a value which
         is an list with two values, one for the minimum cost and one
         for the maximum cost.

       Slicing is not supported.

       This class is (intentionally) optimized for WORM access
       patterns. In-place replacement of items is expensive as it requires
       re-scanning the entire container again to recompute costs.'''
    def __init__(self, data=None):
        super().__init__()
        self._data = list()

        if data:
            for i in data:
                self.append(i)

    def __repr__(self):
        return f'R35List({ self.cost }, { self._data })'

    def __getitem__(self, index):
        if not isinstance(index, int):
            raise IndexError(f'{ index } is not a supported index for R35List objects.')

        if index < -len(self._data) or index >= len(self._data):
            raise IndexError('R35List index out of range')

        return self._data[index]

    def __setitem__(self, index, value):
        if not isinstance(index, int):
            raise IndexError(f'{ index } is not a supported index for R35List objects.')

        if index < -len(self._data) or index >= len(self._data):
            raise IndexError('R35List assignment index out of range')

        self._data[index] = value
        self._recompute_costs()

    def __delitem__(self, index):
        if not isinstance(index, int):
            raise IndexError(f'{ index } is not a supported index for R35List objects.')

        if index < -len(self._data) or index >= len(self._data):
            raise IndexError('R35List assignment index out of range')

        del self._data[index]
        self._recompute_costs()

    def _recompute_costs(self):
        self._costs.reset()

        for item in self._data:
            match self._get_costs(item):
                case None:
                    pass
                case (cost_min, cost_max):
                    self._costs.add(cost_min)
                    self._costs.add(cost_max)

    def insert(self, index, item):
        self._data.insert(index, item)

        match self._get_costs(item):
            case None:
                pass
            case (cost_min, cost_max):
                self._costs.add(cost_min)
                self._costs.add(cost_max)
