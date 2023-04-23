# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

'''Data agent for handling item categories.'''

import logging

from . import agent
from ..common import DATA_ROOT, yaml

logger = logging.getLogger(__name__)


class CategoryAgent(agent.Agent):
    def __init__(self, dataset, pool, name, logger=logger):
        super().__init__(dataset, pool, name, logger)

    @staticmethod
    def _loader(name):
        with open(DATA_ROOT / 'category.yaml') as f:
            return yaml.load(f)

    async def random(self, rank=None):
        return await super().random_compound(rank)
