# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from typing import Any, NoReturn, cast

from .item import WeightedValue
from .retcode import Ret
from ..common import make_weighted_entry, rnd


class RenderMap(Mapping):
    '''Immutable mapping used for grouped render data types.

       Keys must be strings that are valid Python identifiers.

       Values must be lists of strings.

       Each key is also exposed as an attribute. When accessing that
       attribute, a random item from the value for that key will be
       returned.'''
    def __init__(self: RenderMap, /, data: Mapping[str, Sequence[str | dict]]) -> None:
        if not (isinstance(data, dict) or
                isinstance(data, Mapping)):
            raise TypeError('Initializer must be a mapping.')

        self._data: dict[str, Sequence[str] | Sequence[WeightedValue]] = dict()

        for k, v in data.items():
            try:
                k = str(k)

                if not k.isidentifier():
                    raise KeyError(f'{k}: RenderMap keys must be valid Python identifiers.')
            except TypeError:
                raise KeyError('RenderMap keys must be strings.')

            if not (isinstance(v, list) or
                    isinstance(v, Sequence)):
                raise ValueError('RenderMap values must be valid sequences.')

            if all(map(lambda x: isinstance(x, str), v)):
                self._data[k] = cast(Sequence[str], v)
            else:
                self._data[k] = [make_weighted_entry(x) for x in cast(Sequence[Mapping[str, Any]], v)]

    def __getattr__(self: RenderMap, key: str, /) -> str | NoReturn:
        data = cast(dict[str, Sequence[str] | Sequence[WeightedValue]], object.__getattribute__(self, '_data'))

        if key in data:
            if all(map(lambda x: isinstance(x, WeightedValue), data[key])):
                ret = rnd(cast(Sequence[WeightedValue], data[key]))
            else:
                ret = rnd(cast(Sequence[str], data[key]))

            if isinstance(ret, Ret):
                raise AttributeError
            else:
                return ret
        else:
            raise AttributeError

    def __len__(self: RenderMap, /) -> int:
        return len(self._data)

    def __getitem__(self: RenderMap, key: str, /) -> Sequence[str | WeightedValue]:
        return self._data[key]

    def __iter__(self: RenderMap, /) -> Iterator[str]:
        return iter(self._data)

    def __contains__(self: RenderMap, key: Any, /) -> bool:
        return key in self._data
