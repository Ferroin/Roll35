# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

'''Data handling for spell classes.'''

from __future__ import annotations

import logging

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from . import agent
from .. import types
from ..common import ismapping
from ..log import log_call_async

if TYPE_CHECKING:
    from . import DataSet

logger = logging.getLogger(__name__)


@dataclass
class ClassesData(agent.AgentData):
    '''Data managed by a ClassesAgent.'''
    classes: types.item.ClassMap


class ClassesAgent(agent.Agent):
    '''A data agent for spellcasting class data.'''
    def __init__(self: ClassesAgent, dataset: DataSet, name: str, /) -> None:
        super().__init__(dataset, name)
        self._data: ClassesData = ClassesData(
            classes=dict()
        )

    @staticmethod
    def _process_data(data: Mapping | Sequence, /) -> ClassesData:
        if not ismapping(data):
            raise TypeError('Class data must be a mapping.')

        classes = dict()

        for k, v in data.items():
            classes[k] = types.item.ClassEntry(name=k, **v)

        for cls in classes.values():
            if cls.duplicate is not None:
                if cls.duplicate not in classes.keys():
                    raise ValueError(f'{ cls.name }’s `duplicate` key references non-existent class { cls.duplicate }')
            elif cls.merge is not None:
                for mcls in cls.merge:
                    if mcls not in classes.keys():
                        raise ValueError(f'{ cls.name }’s `merge` key references non-existent class { mcls }')

        return ClassesData(
            classes=classes
        )

    @log_call_async(logger, 'blocking get class data')
    async def W_classdata(self: ClassesAgent, /) -> types.item.ClassMap:
        '''Return the bulk data, but wait until the agent is ready.'''
        await self._ready.wait()
        return self._data.classes

    @log_call_async(logger, 'get class data')
    @types.check_ready(logger)
    async def classdata(self: ClassesAgent, /) -> types.item.ClassMap:
        '''Return the bulk data.'''
        return self._data.classes

    @log_call_async(logger, 'get class list')
    @types.check_ready(logger)
    async def classes(self: ClassesAgent, /) -> Sequence[str]:
        '''Return the list of classes.'''
        return list(self._data.classes.keys())

    @log_call_async(logger, 'get class')
    @types.check_ready(logger)
    async def get_class(self: ClassesAgent, /, cls: str) -> types.item.ClassEntry:
        '''Return the data for a specific class, by name.'''
        return self._data.classes[cls]
