# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

import collections.abc

from .container import R35Container


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
        return f'R35Map({ self.costs }, { self._data })'

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
