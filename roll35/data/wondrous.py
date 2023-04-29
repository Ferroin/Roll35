# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

'''Data handling for wondrous item slots.'''

from . import agent
from ..common import check_ready, rnd


class WondrousAgent(agent.Agent):
    @staticmethod
    def _process_data(data):
        return data

    @check_ready
    @agent.ensure_costs
    async def random(self, mincost=None, maxcost=None):
        return rnd(agent.costfilter(self._data, mincost, maxcost))

    @check_ready
    async def slots(self):
        return list(map(lambda x: x['value'], self._data))
