# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

'''Item data handling for roll35.'''

from __future__ import annotations

import asyncio

from collections.abc import Mapping
from typing import TYPE_CHECKING, Union

from ..common import yaml
from ..types import Ret

from .constants import DATA_ROOT

from .category import CategoryAgent
from .classes import ClassesAgent
from .compound import CompoundAgent
from .ordnance import OrdnanceAgent
from .ranked import RankedAgent
from .settlement import SettlementAgent
from .spell import SpellAgent
from .wondrous import WondrousAgent

if TYPE_CHECKING:
    from concurrent.futures import Executor

agents = {
    'category': CategoryAgent,
    'classes': ClassesAgent,
    'compound': CompoundAgent,
    'ordnance': OrdnanceAgent,
    'ranked': RankedAgent,
    'settlement': SettlementAgent,
    'spell': SpellAgent,
    'wondrous': WondrousAgent,
}

AnyAgent = Union[
    CategoryAgent,
    ClassesAgent,
    CompoundAgent,
    OrdnanceAgent,
    RankedAgent,
    SettlementAgent,
    SpellAgent,
    WondrousAgent
]


class DataSet:
    '''Represents a dataset for the module.

       Data must be loaded at runtime by calling and awaiting the
       `load_data()` coroutine.

       Individual categories within the data set are accessed by name
       via subscripting.'''
    def __init__(self: DataSet, /):
        self._agents: Mapping[str, AnyAgent] = dict()
        self.ready = False

        with open(DATA_ROOT / 'structure.yaml') as f:
            structure = yaml.load(f)

        self.renderdata = structure['renderdata']
        self._types: Mapping[str, set[str]] = {k: set() for k in agents.keys()}

        for item in structure['agents']:
            self._agents[item['name']] = agents[item['type']](self, item['name'])
            self._types[item['type']].add(item['name'])

    def __getitem__(self: DataSet, key: str, /) -> AnyAgent:
        return self._agents[key]

    @property
    def types(self: DataSet, /) -> Mapping[str, set[str]]:
        '''A list of the categories within the data set, grouped by type.'''
        return self._types

    async def load_data(self: DataSet, pool: Executor, /) -> Ret:
        '''Load the data for this dataset.'''
        if not self.ready:
            loaders = []

            for agent in self._agents.values():
                loaders.append(asyncio.create_task(agent.load_data(pool)))

            await asyncio.gather(*loaders)

        self.ready = True

        return Ret.OK


def _inspect_dataset() -> DataSet:
    '''Return a DataSet instance with data loaded for inspection.

       This is intended for developer usage only, and _should not_
       be called from module code.'''
    from concurrent.futures import ProcessPoolExecutor

    pool = ProcessPoolExecutor()
    ds = DataSet()

    async def setup() -> None:
        await ds.load_data(pool)

    asyncio.run(setup())

    return ds
