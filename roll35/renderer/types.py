# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

'''Data types used by the renderer.'''

import collections.abc
import logging

from ..common import expand_weighted_list, rnd

logger = logging.getLogger(__name__)


class RenderData(collections.abc.Mapping):
    '''Data used to render templates.'''
    def __init__(self, data, logger=logger):
        self._data = data
        self.logger = logger

    def __len__(self):
        return len(self._data)

    def __getitem__(self, key):
        match self._data[key]:
            case {'type': 'grouped_proportional', 'data': data}:
                ret = dict()

                for group in data:
                    ret[group] = expand_weighted_list(data[group])

                return ret
            case {'type': 'flat_proportional', 'data': data}:
                return expand_weighted_list(data)
            case {'type': 'grouped', 'data': data}:
                return data
            case {'type': 'flat', 'data': data}:
                return data

    def __iter__(self):
        return list(self._data.keys())

    def __contains__(self, item):
        return item in self._data

    def random(self, key, group=None):
        match self._data[key]:
            case {'type': 'grouped_proportional', 'data': data} | \
                 {'type': 'grouped', 'data': data}:
                return rnd(data[group])
            case {'type': 'flat_proportional', 'data': data} | \
                 {'type': 'flat', 'data': data}:
                return rnd(data)
