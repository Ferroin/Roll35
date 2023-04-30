# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

import collections.abc

from .container import R35Container


class R35List(R35Container, collections.abc.MutableSequence):
    '''A simple cost-tracking list class.

       Costs are only updated for contained items that are one of:
       - Another roll35.types.R35Container.
       - A mapping with a key called 'cost' that has a value that is
         either an integer or a float.
       - A mapping with a key called 'costrange' that has a value which
         is an list with two values, one for the minimum cost and one
         for the maximum cost.

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
        return f'R35List({ self.costs }, { self._data })'

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
        '''Add item to the list at index.'''

        self._data.insert(index, item)

        match self._get_costs(item):
            case None:
                pass
            case (cost_min, cost_max):
                self._costs.add(cost_min)
                self._costs.add(cost_max)
