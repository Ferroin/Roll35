# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

'''Data handling for settlements properties.'''

from collections.abc import Sequence
from itertools import repeat

from . import agent
from ..common import check_ready
from ..retcode import Ret


class PopulationMap(Sequence):
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
    def __init__(self, dataset, pool, name):
        super().__init__(dataset, pool, name)

    @staticmethod
    def _process_data(data):
        return {
            'by_name': {x['name']: x for x in data},
            'by_population': PopulationMap(data),
        }

    @check_ready
    async def get_by_name(self, name):
        if name in self._data['by_name']:
            return self._data['by_name'][name]
        else:
            return Ret.NO_MATCH

    @check_ready
    async def get_by_population(self, population):
        return self._data['by_population'][population]
