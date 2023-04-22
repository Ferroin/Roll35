# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

'''Data agent for handling item categories.'''

import logging

from . import agent
from ..common import DATA_ROOT, yaml

logger = logging.getLogger(__name__)


class CategoryAgent(agent.Agent):
    def __init__(self, pool, logger=logger):
        self.name = 'category'
        super().__init__(pool, logger)

    @staticmethod
    def _loader(name):
        with open(DATA_ROOT / 'category.yaml') as f:
            return yaml.load(f)

    async def random(self, rank=None):
        return await super().random_compound(rank)
