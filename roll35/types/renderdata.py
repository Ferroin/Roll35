# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

import collections.abc

from .rendermap import RenderMap

from ..common import rnd


class RenderData(collections.abc.Mapping):
    '''Top level type for data used to render templates.'''
    def __init__(self, data):
        self._data = dict()

        for k, v in data.items():
            try:
                k = str(k)

                if not k.isidentifier():
                    raise KeyError(f'{ k }: RenderData keys must be valid Python identifiers.')
            except TypeError:
                raise KeyError('RenderData keys must be strings.')

            match v:
                case {'type': 'grouped_proportional', 'data': data}:
                    self._data[k] = RenderMap(data)
                case {'type': 'grouped', 'data': data}:
                    self._data[k] = RenderMap(data)
                case {'type': 'flat_proportional', 'data': data}:
                    self._data[k] = data
                case {'type': 'flat', 'data': data}:
                    self._data[k] = data

    def __getattr__(self, key):
        data = object.__getattribute__(self, '_data')

        if key in data:
            if isinstance(data[key], RenderMap):
                return data[key]
            else:
                return rnd(data[key])
        else:
            raise AttributeError

    def __len__(self):
        return len(self._data)

    def __getitem__(self, key):
        return self._data[key]

    def __iter__(self):
        return list(self._data)

    def __contains__(self, key):
        return key in self._data
