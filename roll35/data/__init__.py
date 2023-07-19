# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

'''Item data handling for roll35.'''

from __future__ import annotations

import asyncio
import logging
import os

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Union, Type
from pathlib import Path

from pydantic import field_validator, BaseModel

from ..common import yaml
from ..types import Ret

from .agent import Agent

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

logger = logging.getLogger(__name__)

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


BUNDLED_DATA_ROOT = Path(__file__).parent / 'files'
DEFAULT_DATA_ROOT = BUNDLED_DATA_ROOT

if (_dr := os.environ.get('R35_DATA_ROOT', None)) is not None:
    try:
        _root = Path(_dr)
    except Exception:
        logger.warning(f'Requested data root path { _dr } does not appear to be a valid path. Using default path instead.')
    else:
        if _root.exists():
            if _root.is_dir():
                if (_root / 'structure.yaml').exists() and (_root / 'structure.yaml').is_file():
                    DEFAULT_DATA_ROOT = _root
                else:
                    logger.warning(f'Requested data root path { _root } does not include a structure.yaml file, using default path instead.')
            else:
                logger.warning(f'Requested data root path { _root } is not a directory. Using default path instead')
        else:
            raise ValueError(f'Requested data root path { _root } does not exist. Using default path instead')


class AgentEntry(BaseModel):
    '''An entry describing a data agent in a dataset.'''
    name: str
    type: str

    @field_validator('type')
    @classmethod
    def check_type(cls: Type[AgentEntry], v: str) -> str:
        if v not in agents:
            raise ValueError(f'Unrecognized agent type in structure file { v }.')

        return v


class StructureData(BaseModel):
    '''Structure data for a dataset.'''
    agents: Sequence[AgentEntry]
    renderdata: str

    @field_validator('agents')
    @classmethod
    def check_agents(cls: Type[StructureData], v: Sequence[AgentEntry]) -> Sequence[AgentEntry]:
        '''Sanity check agent information.'''
        if len({x.name for x in v}) != len(v):
            raise ValueError('Duplicate names found in agent list.')

        return v


StructureData.update_forward_refs()


class DataSet:
    '''Represents a dataset for the module.

       Data must be loaded at runtime by calling and awaiting the
       `load_data_async()` coroutine.

       Individual categories within the data set are accessed by name
       via subscripting.'''
    def __init__(self: DataSet, /, *, src: Path = DEFAULT_DATA_ROOT):
        self._agents: Mapping[str, Agent] = dict()
        self.src = src
        self.ready = False

        if not src.exists():
            raise ValueError(f'Requested data source path { src } does not exist.')

        if not src.is_dir():
            raise ValueError(f'Requested data source path { src } is not a directory.')

        with open(self.src / 'structure.yaml') as f:
            structure = StructureData(**yaml.load(f))

        self.renderdata = structure.renderdata
        self._types: Mapping[str, set[str]] = {k: set() for k in agents.keys()}

        for item in structure.agents:
            self._agents[item.name] = agents[item.type](self, item.name)
            self._types[item.type].add(item.name)

    def __getitem__(self: DataSet, key: str, /) -> Agent:
        return self._agents[key]

    def __contains__(self: DataSet, key: str, /) -> bool:
        return key in self._agents

    @property
    def types(self: DataSet, /) -> Mapping[str, set[str]]:
        '''A list of the categories within the data set, grouped by type.'''
        return self._types

    def load_data(self: DataSet, /) -> Ret:
        '''Load the data for this dataset.'''
        if not self.ready:
            self._agents['classes'].load_data()
            self._agents['spell'].load_data()

            for agent in [v for (k, v) in self._agents.items() if k not in {'classes', 'spell'}]:
                agent.load_data()

            self.ready = True

        return Ret.OK

    async def load_data_async(self: DataSet, pool: Executor, /) -> Ret:
        '''Load the data for this dataset.'''
        if not self.ready:
            classes_loader = asyncio.create_task(self._agents['classes'].load_data_async(pool))
            loaders = [classes_loader]

            for agent in [v for (k, v) in self._agents.items() if k != 'classes']:
                loaders.append(asyncio.create_task(agent.load_data_async(pool)))

            await asyncio.gather(*loaders)

            self.ready = True

        return Ret.OK


def _get_dataset_async(src: Path = DEFAULT_DATA_ROOT) -> DataSet:
    '''Return a DataSet instance with data loaded for inspection.

       This is intended to allow testing of the async data loading
       interface. If you just want a dataset to work with without having
       to deal with asyncio, instead instantiate DataSet directly and
       use the `load_data()` method to synchronously load the data.

       Behavior of this function is _not_ guaranteed in any way across
       versions of Roll35, and it should thus not be used by external
       code. If you need to construct a DataSet instance to use in
       your own code, you should instantiate the DataSet class directly
       instead.'''
    from concurrent.futures import ProcessPoolExecutor

    pool = ProcessPoolExecutor()
    ds = DataSet(src=src)

    async def setup() -> None:
        await ds.load_data_async(pool)

    asyncio.run(setup())

    pool.shutdown()

    return ds


def test_dataset(src: Path = DEFAULT_DATA_ROOT) -> int:
    '''Test a data set located at src.

       This verifies loading the data (including the renderer data),
       but does nothing more. Throws appropriate errors if there are
       issues with the dataset.'''
    from concurrent.futures import ProcessPoolExecutor

    from ..renderer import Renderer

    pool = ProcessPoolExecutor()
    ds = DataSet(src=src)
    renderer = Renderer(ds)

    async def setup() -> None:
        await ds.load_data_async(pool)
        await renderer.load_data(pool)

    asyncio.run(setup())

    pool.shutdown()

    return 0
