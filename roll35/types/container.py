# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

import abc
import collections.abc

from .range import R35Range


class R35Container(abc.ABC, collections.abc.Collection):
    '''Base class used by roll35 container types.

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
