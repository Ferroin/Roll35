# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

'''Item data handling for roll35.'''

import asyncio

from pathlib import Path

from ..common import yaml

from .category import CategoryAgent
from .compound import CompoundAgent
from .ordnance import OrdnanceAgent
from .ranked import RankedAgent
from .spell import SpellAgent
from .wondrous import WondrousAgent

DATA_ROOT = Path(__file__).parent / 'files'

agents = {
    'category': CategoryAgent,
    'compound': CompoundAgent,
    'ordnance': OrdnanceAgent,
    'ranked': RankedAgent,
    'spell': SpellAgent,
    'wondrous': WondrousAgent,
}


class DataSet:
    def __init__(self, pool):
        self._agents = dict()
        self.ready = False

        with open(DATA_ROOT / 'structure.yaml') as f:
            structure = yaml.load(f)

        self.renderdata = structure['renderdata']

        for item in structure['agents']:
            self._agents[item['name']] = agents[item['type']](pool, item['name'])

    def __getitem__(self, key):
        return self._agents[key]

    async def load_data(self):
        '''Load the data for this dataset.'''
        if not self.ready:
            loaders = []

            for agent in self._agents.values():
                loaders.append(agent.load_data())

            await asyncio.gather(*loaders)

        self.ready = True
