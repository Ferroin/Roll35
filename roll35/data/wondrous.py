# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

'''Data handling for wondrous item slots.'''

import logging

from . import agent
from ..common import DATA_ROOT, yaml, rnd

logger = logging.getLogger(__name__)


class WondrousAgent(agent.Agent):
    def __init__(self, pool, logger=logger):
        self.name = 'wondrous'
        super().__init__(pool, logger)

    @staticmethod
    def _loader(_):
        with open(DATA_ROOT / 'wondrous.yaml') as f:
            return yaml.load(f)

    def early_load(self):
        if not self._ready:
            self.logger.info(f'Early loading { self.name } data.')
            self._data = self._loader(True)
            self.logger.info(f'Finished early loading { self.name } data.')

            self._ready = True

        return True

    async def random(self):
        if self._ready:
            return rnd(self._data)

        return False

    def sslots(self):
        if self._ready:
            return list(map(lambda x: x['value'], self._data))

        return False

    async def slots(self):
        return self.sslots()
