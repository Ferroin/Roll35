# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

'''Data handling for wondrous item slots.'''

import logging

from . import agent
from ..common import check_ready, DATA_ROOT, yaml, rnd

logger = logging.getLogger(__name__)


class WondrousAgent(agent.Agent):
    def __init__(self, dataset, pool, name='wondrous', logger=logger):
        super().__init__(dataset, pool, name, logger)

    @staticmethod
    def _loader(_):
        with open(DATA_ROOT / 'wondrous.yaml') as f:
            return yaml.load(f)

    @check_ready
    @agent.ensure_costs
    async def random(self, mincost=None, maxcost=None):
        return rnd(agent.costfilter(self._data, mincost, maxcost))

    @check_ready
    async def slots(self):
        return list(map(lambda x: x['value'], self._data))
