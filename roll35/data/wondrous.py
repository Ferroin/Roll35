# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

'''Data handling for wondrous item slots.'''

from __future__ import annotations

import logging

from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from . import agent
from .. import types
from ..common import rnd, make_weighted_entry, ismapping
from ..log import log_call_async

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from . import DataSet

logger = logging.getLogger(__name__)


@dataclass
class WondrousData(agent.AgentData):
    '''Data handled by a WondrousAgent.'''
    slots: Sequence[types.WeightedEntry]


class WondrousAgent(agent.Agent):
    '''Data agent for wondrous item data.'''
    def __init__(self: WondrousAgent, dataset: DataSet, name: str) -> None:
        super().__init__(dataset, name)
        self._data: WondrousData = WondrousData(
            slots=[]
        )

    @staticmethod
    def _process_data(data: Mapping | Sequence) -> WondrousData:
        if ismapping(data):
            raise ValueError('Wondrous data must be a sequence.')

        slots = []

        for entry in data:
            try:
                slots.append(make_weighted_entry(entry))
            except TypeError:
                raise RuntimeError(f'Invalid wondrous item slot entry: { entry }')

        return WondrousData(
            slots=slots,
        )

    @agent.ensure_costs
    @log_call_async(logger, 'roll random wondrous item slot')
    @types.check_ready(logger)
    async def random(self: WondrousAgent, mincost=None, maxcost=None) -> str | types.Ret:
        '''Return a random slot, possibly limited by cost.'''
        return cast(str | types.Ret, rnd(agent.costfilter(self._data.slots, mincost, maxcost)))

    @log_call_async(logger, 'get wondrous item slots')
    @types.check_ready(logger)
    async def slots(self: WondrousAgent) -> list[str]:
        '''Return a list of known slots.'''
        return list(map(lambda x: cast(str, x.value), self._data.slots))
