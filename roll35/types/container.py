# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

from __future__ import annotations

import abc

from collections.abc import Collection, Iterator
from typing import Any, TypeVar

from .range import R35Range
from .item import Item, BaseItem, Cost

T = TypeVar('T')


class R35Container(abc.ABC, Collection):
    '''Base class used by roll35 container types.'''
    def __init__(self: R35Container, /) -> None:
        self._data: Collection | None = None
        self._costs = R35Range()

    def __len__(self: R35Container, /) -> int:
        if self._data is not None:
            return len(self._data)
        else:
            return 0

    def __iter__(self: R35Container, /) -> Iterator:
        if self._data is not None:
            return self._data.__iter__()
        else:
            return iter(())

    def __contains__(self: R35Container, key: Any, /) -> bool:
        if self._data is not None:
            return key in self._data
        else:
            return False

    @property
    def costs(self: R35Container, /) -> R35Range:
        '''A R35Range instance that tracks the costs of items added to the container.'''
        return self._costs

    @staticmethod
    def _get_costs(item: Item | R35Container | Any, /) -> tuple[Cost, Cost] | None:
        match item:
            case R35Container(costs=R35Range()):
                item.sync()
                return (item.costs.min, item.costs.max)
            case BaseItem(costrange=[low, high]):
                return (low, high)
            case BaseItem(cost=cost) if cost is not None and cost != 'varies':
                return (cost, cost)
        return None

    def sync(self: R35Container, /) -> None:
        '''Recompute the costs for this container.'''
        self._recompute_costs()

    @abc.abstractmethod
    def _recompute_costs(self: R35Container, /) -> None:
        return None
