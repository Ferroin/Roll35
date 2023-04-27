# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

'''Data types used by the renderer.'''

import collections.abc
import logging

from ..common import expand_weighted_list, rnd

logger = logging.getLogger(__name__)


class RenderMap(collections.abc.Mapping):
    '''Immutable mapping used for grouped render data types.

       Keys must be strings that are valid Python identifiers.

       Values must be lists.

       Each key is also exposed as an attribute. When accessing that
       attribute, a random item from the value for that key will be
       returned.'''
    def __init__(self, data):
        if not (isinstance(data, dict) or
                isinstance(data, collections.abc.Mapping)):
            raise TypeError('Initializer must be a mapping.')

        for k, v in data.items():
            try:
                k = str(k)

                if not k.isidentifier():
                    raise KeyError(f'{ k }: RenderMap keys must be valid Python identifiers.')
            except TypeError:
                raise KeyError('RenderMap keys must be strings.')

            if not (isinstance(v, list) or
                    isinstance(v, collections.abc.Sequence)):
                raise ValueError('RenderMap values must be valid sequences.')

        self._data = data

    def __getattr__(self, key):
        data = object.__getattribute__(self, '_data')

        if key in data:
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
