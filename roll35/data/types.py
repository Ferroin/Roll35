# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

'''Data type definitons.'''

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


class R35Costs:
    '''A simple container for tracking cost ranges.

       Provides two properties, min and max, with some basic sanity checks
       to ensure correct behavior, together with a basic __contains__
       method that simply indicates if a value is between min and max
       inclusive.'''
    MIN_VALUE = 0
    MAX_VALUE = float('inf')

    def __init__(self):
        self._min = self.MIN_VALUE
        self._max = self.MAX_VALUE

    def __contains__(self, v):
        return v >= self._min and v <= self._max

    @staticmethod
    def _typecheck(v):
        return isinstance(v, int) or isinstance(v, float)

    @classmethod
    def _rangecheck(cls, v):
        return v >= cls.MIN_VALUE and v <= cls.MAX_VALUE

    @staticmethod
    def valid(v):
        '''Check if a given value is a valid cost value.'''
        if R35Costs._typecheck(v):
            return R35Costs._rangecheck(v)
        else:
            return False

    def reset(self):
        self.min = self.MIN_VALUE
        self.max = self.MAX_VALUE

    @property
    def min(self):
        return self._min

    @min.setter
    def min(self, v):
        if self.__class__._typecheck(v):
            if self.__class__._rangecheck(v):
                self._min = v

                if self._min > self._max:
                    self._max = self._min
            else:
                raise ValueError('Minimum cost must be within the range { self.MIN_VALUE } and { self.MAX_VALUE }.')
        else:
            raise TypeError('Minimum cost must be an integer or float.')

    @property
    def max(self):
        return self._max

    @max.setter
    def max(self, v):
        if self.__class__._typecheck(v):
            if self.__class__._rangecheck(v):
                self._max = v

                if self._max < self._min:
                    self._min = self._max
            else:
                raise ValueError('Maximum cost must be within the range { self.MIN_VALUE } and { self.MAX_VALUE }.')
        else:
            raise TypeError('Maximum cost must be an integer or float.')


class R35Container:
    '''Base class used by R35Map and R35List.

       This exists just to minimize code duplication.'''
    def __init__(self):
        self._costs = R35Costs()

    def __len__(self):
        return len(self._data)

    def __iter__(self):
        return self._data.__iter__()

    def __reversed__(self):
        return reversed(self._data)

    def __contains__(self, key):
        return key in self._data

    @property
    def costs(self):
        return self._costs

    @staticmethod
    def _get_costs(item):
        match item:
            case R35Container(costs=R35Costs(min=low, max=high)):
                return (low, high)
            case {'costrange': [low, high]} if R35Costs.valid(low) and R35Costs.valid(high):
                return (low, high)
            case {'cost': cost} if R35Costs.valid(cost):
                return (cost, cost)
            case _:
                return None


class R35Map(R35Container):
    '''A simple cost-tracking mapping class.

       This implements the basic mapping protocol, plus a handful of
       dict methods to make it easier to use.

       It also maintains a property called costs, which is a
       roll35.types.R35Costs object that tracks the minimum and maximum
       cost of items that have been added to the mapping.

       Costs are only updated for contained items that are one of:
       - Another roll35.types.R35Map instance.
       - A roll35.types.R35List instance.
       - A mapping with a key called 'cost' that has a value that is
         either an integer or a float.
       - A mapping with a key called 'costrange' that has a value which
         is an list with two values, one for the minimum cost and one
         for the maximum cost.

       Keys must be strings or integers.

       This class is (intentionally) optimized for WORM access
       patterns.'''
    def __init__(self, data=None):
        super().__init__()
        self._data = dict()

        if data:
            for k, v in data.items():
                self[k] = v

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
                self._costs.min = min(self._costs.min, cost_min)
                self._costs.max = max(self._costs.max, cost_max)

    def __delitem__(self, key):
        if key in self._data:
            del self._data[key]

            self._costs.reset()

            for item in self._data.values():
                match self._get_costs(item):
                    case None:
                        pass
                    case (cost_min, cost_max):
                        self._costs.min = min(self._costs.min, cost_min)
                        self._costs.max = max(self._costs.max, cost_max)
        else:
            raise KeyError(key)

    def items(self):
        return self._data.items()

    def keys(self):
        return self._data.keys()

    def values(self):
        return self._data.values()


class R35List(R35Container):
    '''A simple cost-tracking list class.

       This implements the basic container protocol, plus an equivalent
       of the list.append() method for simpler usage.

       It also maintains a property called costs, which is a
       roll35.types.R35Costs object that tracks the minimum and maximum
       cost of items that have been added to the mapping.

       Costs are only updated for contained items that are one of:
       - Another roll35.types.R35Map instance.
       - A roll35.types.R35List instance.
       - A mapping with a key called 'cost' that has a value that is
         either an integer or a float.
       - A mapping with a key called 'costrange' that has a value which
         is an list with two values, one for the minimum cost and one
         for the maximum cost.

       Slicing is not supported.

       This class is (intentionally) optimized for append-only WORM
       access patterns.'''
    def __init__(self, data=None):
        super().__init__()
        self._data = list()

        if data:
            for i in data:
                self.append(i)

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
                    self._costs.min = min(self._costs.min, cost_min)
                    self._costs.max = max(self._costs.max, cost_max)

    def append(self, item):
        '''Append an item to the list.'''
        self._data.append(item)

        match self._get_costs(item):
            case None:
                pass
            case (cost_min, cost_max):
                self._costs.min = min(self._costs.min, cost_min)
                self._costs.max = max(self._costs.max, cost_max)
