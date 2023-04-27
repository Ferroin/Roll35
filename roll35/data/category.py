# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

'''Data agent for handling item categories.'''

import logging

from . import agent
from . import constants
from ..common import check_ready

logger = logging.getLogger(__name__)


class CategoryAgent(agent.Agent):
    def __init__(self, dataset, pool, name, logger=logger):
        super().__init__(dataset, pool, name, logger)

    @staticmethod
    def _process_data(data):
        data['categories'] = set()

        for rank in constants.RANK:
            for cat in [x['value'] for x in data[rank]]:
                data['categories'].add(cat)

        return data

    async def random(self, rank=None):
        return await super().random_compound(rank=rank)

    @check_ready
    async def categories(self):
        return self._data['categories']
