# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

from __future__ import annotations

from collections.abc import Mapping, Sequence, Iterator
from typing import TypedDict, Literal, Union, Dict, Any, cast

from .item import WeightedValue
from .rendermap import RenderMap
from ..common import rnd, make_weighted_entry


class TFlatEntry(TypedDict):
    '''A type definition for a flat list entry in the render data.'''
    type: Literal['flat']
    data: Sequence[str]


class TFlatProportionalEntry(TypedDict):
    '''A type definition for a flat proportional list entry in the render data.'''
    type: Literal['flat_proportional']
    data: Sequence[WeightedValue]


class TGroupedEntry(TypedDict):
    '''A type definition for a grouped list entry in the render data.'''
    type: Literal['grouped']
    data: Dict[str, Sequence[str]]


class TGroupedProportionalEntry(TypedDict):
    '''A type definition for a grouped proportional list entry in the render data.'''
    type: Literal['grouped_proportional']
    data: Dict[str, Sequence[WeightedValue]]


TRenderEntry = Union[
    TFlatEntry,
    TFlatProportionalEntry,
    TGroupedEntry,
    TGroupedProportionalEntry,
]


class RenderData(Mapping):
    '''Top level type for data used to render templates.

       This is a relatively simple immutable mapping with some extra
       logic added in.

       Keys must be strings that are valid Python identifiers.

       Each key is also exposed as an attribute. When accessing that
       attribute, a random item from the value for that key will be
       returned.'''
    def __init__(self: RenderData, /, data: Mapping[str, TRenderEntry]) -> None:
        self._data: dict[str, RenderMap | Sequence[str] | Sequence[WeightedValue]] = dict()

        for k, v in data.items():
            try:
                k = str(k)

                if not k.isidentifier():
                    raise KeyError(f'{ k }: RenderData keys must be valid Python identifiers.')
            except TypeError:
                raise KeyError('RenderData keys must be strings.')

            # The casts below are needed to make some type checkers behave
            # correctly as they incorrectly assume that `d` is the same
            # type as `data`, even though it should not be interpreted
            # as such per the typing of `data`.
            match v:
                case {'type': 'grouped_proportional', 'data': d}:
                    self._data[k] = RenderMap(cast(Mapping[str, Sequence[Dict]], d))
                case {'type': 'grouped', 'data': d}:
                    self._data[k] = RenderMap(cast(Mapping[str, Sequence[str]], d))
                case {'type': 'flat_proportional', 'data': d}:
                    self._data[k] = [make_weighted_entry(x) for x in cast(Sequence[Mapping[str, Any]], d)]
                case {'type': 'flat', 'data': d}:
                    self._data[k] = cast(Sequence[str], d)
                case _:
                    raise ValueError(f'{ v } is not a valid value for RenderData.')

    def __getattr__(self: RenderData, key: str, /) -> RenderMap | str:
        data = object.__getattribute__(self, '_data')

        if key in data:
            if isinstance(data[key], RenderMap):
                return cast(RenderMap, data[key])
            else:
                ret = rnd(data[key])

                if isinstance(ret, str):
                    return ret
                else:
                    raise AttributeError
        else:
            raise AttributeError

    def __len__(self: RenderData, /) -> int:
        return len(self._data)

    def __getitem__(self: RenderData, key: str, /) -> RenderMap | Sequence[str] | Sequence[WeightedValue]:
        return self._data[key]

    def __iter__(self: RenderData, /) -> Iterator:
        return iter(self._data)

    def __contains__(self: RenderData, key: Any, /) -> bool:
        return key in self._data
