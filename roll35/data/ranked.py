# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

'''Data handling for ranked item lists.'''

import logging

from . import agent
from ..common import DATA_ROOT, yaml

logger = logging.getLogger(__name__)


class RankedAgent(agent.Agent):
    def __init__(self, dataset, pool, name, logger=logger):
        super().__init__(dataset, pool, name, logger)

    @staticmethod
    def _loader(name):
        with open(DATA_ROOT / f'{ name }.yaml') as f:
            data = yaml.load(f)

        ret = agent.process_ranked_itemlist(data)

        return ret

    async def random(self, **kwargs):
        return await super().random_ranked(**kwargs)
