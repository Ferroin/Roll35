# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

'''Data handling for settlements properties.'''

from __future__ import annotations

import logging

from collections.abc import Sequence, Mapping
from dataclasses import dataclass
from itertools import repeat
from typing import TYPE_CHECKING, Literal, cast, overload

from . import agent
from .. import types
from ..common import check_ready, ismapping
from ..log import log_call_async

if TYPE_CHECKING:
    from . import DataSet

    ItemSlots = Sequence[int] | Literal['any']

logger = logging.getLogger(__name__)


@dataclass
class SettlementEntry:
    '''Describes a settlement.'''
    name: str
    population: int | None
    base: types.item.Cost
    purchase: types.item.Cost
    casting: int
    minor: ItemSlots
    medium: ItemSlots
    major: ItemSlots


class PopulationMap(Sequence):
    '''A sequence-like container for looking up settlement info by population.

       The data used to initialize an instance should be a sequence of
       dicts with `population` keys that map to positive integers. There
       may be exactly one item with the `population` key having a value of
       `None`. If such an entry exists, that entry will be returned for
       any index above the largest value of any other `population` key.

       Indexing the resultant sequence will return the item which has
       that specific value for it’s `population` key.

       Indexes of 0 or less are invalid.

       Indexes of more than the highest population of any item in the
       sequence will return the item with the highest population.

       Internally, this only stores a single instance of each item in
       the initial data set, and then constructs a lookup table to map
       from the population to the actual item. '''
    def __init__(self: PopulationMap, data: Sequence[SettlementEntry]) -> None:
        if not data:
            return

        self._data = {x.name: x for x in data}
        self._lookup: list[str] = []

        popitems = sorted(
            filter(
                lambda x: x.population is not None,
                data
            ),
            key=lambda x: cast(int, x.population)
        )

        for item in popitems:
            self._lookup += repeat(item.name, cast(int, item.population) - len(self._lookup))

        self._maxpop = list(
            filter(
                lambda x: x.population is None,
                data
            )
        )[0]

    @overload
    def __getitem__(self: PopulationMap, v: int) -> SettlementEntry:
        pass

    @overload
    def __getitem__(self: PopulationMap, v: slice) -> Sequence[SettlementEntry]:
        pass

    def __getitem__(self: PopulationMap, v):
        if isinstance(v, slice):
            ret: list[SettlementEntry] = []

            for i in range(v.start, v.stop, v.step):
                ret.append(self[i])

            return ret
        elif v < 1:
            raise IndexError(v)
        elif v > len(self._lookup):
            return self._maxpop
        else:
            return self._data[self._lookup[v]]

    def __len__(self: PopulationMap) -> int:
        return len(self._lookup) + 1


@dataclass
class SettlementData(agent.AgentData):
    '''Data handled by a SettlementAgent.'''
    name: Mapping[str, SettlementEntry]
    population: PopulationMap


class SettlementAgent(agent.Agent):
    '''Data agent for settlement data.'''
    def __init__(self: SettlementAgent, dataset: DataSet, name: str) -> None:
        super().__init__(dataset, name)
        self._data: SettlementData = SettlementData(
            name=dict(),
            population=PopulationMap([]),
        )

    @staticmethod
    def _process_data(data: Mapping | Sequence) -> SettlementData:
        if ismapping(data):
            raise ValueError('Settlement data must be a sequence')

        entries: list[SettlementEntry] = []

        for item in data:
            try:
                entries.append(SettlementEntry(**item))
            except TypeError:
                raise RuntimeError(f'Invalid settlement entry: { item }')

        return SettlementData(
            name={x.name: x for x in entries},
            population=PopulationMap(entries),
        )

    @log_call_async(logger, 'get settlement by name')
    @check_ready
    async def get_by_name(self: SettlementAgent, name: str) -> SettlementEntry | types.Ret:
        '''Look up a settlement category by name.'''
        if name in self._data.name:
            return self._data.name[name]
        else:
            return types.Ret.NO_MATCH

    @log_call_async(logger, 'get settlement by population')
    @check_ready
    async def get_by_population(self: SettlementAgent, population: int) -> SettlementEntry:
        '''Look up a settlement category by population.'''
        return self._data.population[population]
