# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

'''Data handling for spell classes.'''

import logging

from . import agent
from ..common import check_ready, DATA_ROOT, yaml

logger = logging.getLogger(__name__)


class ClassesAgent(agent.Agent):
    def __init__(self, dataset, pool, name='classes', logger=logger):
        super().__init__(dataset, pool, name, logger)

    @staticmethod
    def _loader(name):
        with open(DATA_ROOT / f'{ name }.yaml') as f:
            return yaml.load(f)

    async def W_classdata(self):
        await self._ready.wait()
        return self._data

    @check_ready
    async def classdata(self):
        return self._data

    @check_ready
    async def classes(self):
        return list(self._data.keys())

    @check_ready
    async def get_class(self, cls):
        return self._data[cls]