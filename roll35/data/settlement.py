# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

'''Data handling for settlements properties.'''

from collections.abc import Sequence
from itertools import repeat

from . import agent
from ..common import check_ready
from ..retcode import Ret


class PopulationMap(Sequence):
    '''A sequence-like container for looking up settlement info by population.

       The data used to initialize an instance should be a sequence of
       dicts with `population` keys that map to positive integers. There
       may be exactly one item with the `population` key having a value of
       `None`. If such an entry exists, that entry will be returned for
       any index above the largest value of any other `population` key.

       Indexing the resultant sequence will return the item which has
       that specific value for it’s `population` key.

       Indexes of 0 or less are invalid.

       Indexes of more than the highest population of any item in the
       sequence will return the item with the highest population.

       Internally, this only stores a single instance of each item in
       the initial data set, and then constructs a lookup table to map
       from the population to the actual item. '''
    def __init__(self, data):
        self._data = {x['name']: x for x in data}
        self._lookup = []

        popitems = sorted(
            filter(
                lambda x: x['population'] is not None,
                data
            ),
            key=lambda x: x['population']
        )

        for item in popitems:
            self._lookup += repeat(item['name'], item['population'] - len(self._lookup))

        self._maxpop = list(
            filter(
                lambda x: x['population'] is None,
                data
            )
        )[0]

    def __getitem__(self, v):
        if v < 1:
            raise IndexError(v)
        elif v > len(self._lookup):
            return self._maxpop
        else:
            return self._data[self._lookup[v]]

    def __len__(self):
        return len(self._lookup) + 1


class SettlementAgent(agent.Agent):
    '''Data agent for settlement data.'''
    @staticmethod
    def _process_data(data):
        return {
            'by_name': {x['name']: x for x in data},
            'by_population': PopulationMap(data),
        }

    @check_ready
    async def get_by_name(self, name):
        '''Look up a settlement category by name.'''
        if name in self._data['by_name']:
            return self._data['by_name'][name]
        else:
            return Ret.NO_MATCH

    @check_ready
    async def get_by_population(self, population):
        '''Look up a settlement category by population.'''
        return self._data['by_population'][population]
