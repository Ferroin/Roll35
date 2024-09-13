# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

from __future__ import annotations

from collections.abc import ItemsView, KeysView, Mapping, MutableMapping, ValuesView
from enum import Enum
from typing import Generic, TypeVar, cast

from .container import R35Container

K = TypeVar('K')
V = TypeVar('V')


class R35Map(R35Container, MutableMapping, Generic[K, V]):
    '''A simple cost-tracking mapping class.

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
    def __init__(self: R35Map, /, data: Mapping[K, V] | None = None):
        super().__init__()
        self._data: dict[K, V] = dict()

        if data is not None:
            for k, v in data.items():
                self[k] = v

    def __repr__(self: R35Map, /) -> str:
        return f'R35Map({self.costs}, {self._data})'

    def __getitem__(self: R35Map, key: K, /) -> V:
        if key in self._data:
            return cast(V, self._data[key])
        else:
            raise KeyError(key)

    def __setitem__(self: R35Map, key: K, value: V, /) -> None:
        if not (isinstance(key, str) or isinstance(key, int) or isinstance(key, Enum)):
            raise KeyError('Only string, integer, and Enum keys are supported by R35Map objects.')

        match self._get_costs(value):
            case None:
                if key in self:
                    del self[key]

                self._data[key] = value
            case (cost_min, cost_max):
                if key in self:
                    del self[key]

                self._data[key] = value
                self._costs.add([cost_min])
                self._costs.add([cost_max])

    def __delitem__(self: R35Map, key: K, /) -> None:
        if key in self._data:
            del self._data[key]

            self._recompute_costs()
        else:
            raise KeyError(key)

    def _recompute_costs(self: R35Map, /) -> None:
        self._costs.reset()

        for item in self._data.values():
            match self._get_costs(item):
                case None:
                    pass
                case (cost_min, cost_max):
                    self._costs.add([cost_min])
                    self._costs.add([cost_max])

    def items(self: R35Map, /) -> ItemsView:
        '''Return a view of the keys and values of the mapping.'''
        return self._data.items()

    def keys(self: R35Map, /) -> KeysView:
        '''Return a view of the keys of the mapping.'''
        return self._data.keys()

    def values(self: R35Map, /) -> ValuesView:
        '''Return a view of the values of the mapping.'''
        return self._data.values()
