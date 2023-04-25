# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

'''Data agent for handling item categories.'''

import logging

from . import agent
from . import types
from ..common import DATA_ROOT, yaml, check_ready

logger = logging.getLogger(__name__)


class CategoryAgent(agent.Agent):
    def __init__(self, dataset, pool, name, logger=logger):
        super().__init__(dataset, pool, name, logger)

    @staticmethod
    def _loader(name):
        with open(DATA_ROOT / f'{ name }.yaml') as f:
            data = yaml.load(f)

        data['categories'] = set()

        for rank in types.RANK:
            for cat in [x['value'] for x in data[rank]]:
                data['categories'].add(cat)

        return data

    async def random(self, rank=None):
        return await super().random_compound(rank=rank)

    @check_ready
    async def categories(self):
        return self._data['categories']
