# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

'''Item data handling for roll35.'''

import asyncio

from pathlib import Path

from ..common import yaml

from .category import CategoryAgent
from .classes import ClassesAgent
from .compound import CompoundAgent, CompoundSpellAgent
from .ordnance import OrdnanceAgent
from .ranked import RankedAgent
from .spell import SpellAgent
from .wondrous import WondrousAgent

DATA_ROOT = Path(__file__).parent / 'files'

agents = {
    'category': CategoryAgent,
    'classes': ClassesAgent,
    'compound': CompoundAgent,
    'compound-spell': CompoundSpellAgent,
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
        self._types = {k: set() for k in agents.keys()}

        for item in structure['agents']:
            self._agents[item['name']] = agents[item['type']](self, pool, item['name'])
            self._types[item['type']].add(item['name'])

    def __getitem__(self, key):
        return self._agents[key]

    @property
    def types(self):
        return self._types

    async def load_data(self):
        '''Load the data for this dataset.'''
        if not self.ready:
            loaders = []

            for agent in self._agents.values():
                loaders.append(asyncio.create_task(agent.load_data()))

            await asyncio.gather(*loaders)

        self.ready = True
