# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

from __future__ import annotations

from collections.abc import MutableSequence, Iterable
from typing import TypeVar, Generic, SupportsIndex, overload, cast

from .container import R35Container
from .item import Item

T = TypeVar('T')


class R35List(R35Container, MutableSequence, Generic[T]):
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
    def __init__(self: R35List, /, data: Iterable[T] | None = None):
        super().__init__()
        self._data: list[T] = list()

        if data is not None:
            for i in data:
                self.append(i)

    def __repr__(self: R35List, /) -> str:
        return f'R35List({ self.costs }, { self._data })'

    @overload
    def __getitem__(self: R35List, index: SupportsIndex, /) -> T: ...

    @overload
    def __getitem__(self: R35List, index: slice, /) -> MutableSequence[T]: ...

    def __getitem__(self: R35List, index: SupportsIndex | slice, /) -> T | MutableSequence[T]:
        match index:
            case SupportsIndex():
                idx = index.__index__()
                if idx < -len(self._data) or idx >= len(self._data):
                    raise IndexError('R35List index out of range')
            case slice():
                pass
            case _:
                raise IndexError(f'{ index } is not a supported index for R35List objects.')

        return self._data[index]

    @overload
    def __setitem__(self: R35List, index: SupportsIndex, value: T, /) -> None: ...

    @overload
    def __setitem__(self: R35List, index: slice, value: Iterable[T], /) -> None: ...

    def __setitem__(self: R35List, index: SupportsIndex | slice, value: T | Iterable[T], /) -> None:
        match index:
            case SupportsIndex():
                self._data[index] = value
            case slice():
                self._data[index] = cast(Iterable[T], value)

        self._recompute_costs()

    @overload
    def __delitem__(self: R35List, index: SupportsIndex, /) -> None: ...

    @overload
    def __delitem__(self: R35List, index: slice, /) -> None: ...

    def __delitem__(self: R35List, index: SupportsIndex | slice, /) -> None:
        del self._data[index]
        self._recompute_costs()

    def _recompute_costs(self: R35List, /) -> None:
        self._costs.reset()

        for item in self._data:
            match self._get_costs(cast(Item, item)):
                case None:
                    pass
                case (cost_min, cost_max):
                    self._costs.add([cost_min])
                    self._costs.add([cost_max])

    def insert(self: R35List, index: int, item: T, /) -> None:
        '''Add item to the list at index.'''
        self._data.insert(index, item)

        match self._get_costs(cast(Item, item)):
            case None:
                pass
            case (cost_min, cost_max):
                self._costs.add([cost_min])
                self._costs.add([cost_max])
