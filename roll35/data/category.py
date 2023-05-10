# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

'''Data handling for item categories.'''

from __future__ import annotations

import logging

from dataclasses import dataclass
from typing import TYPE_CHECKING

from . import agent
from .. import types
from ..common import make_weighted_entry, ismapping, bad_return
from ..log import log_call_async

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from . import DataSet

logger = logging.getLogger(__name__)


@dataclass
class CategoryData(agent.AgentData):
    '''Data managed by a CategoryAgent.'''
    categories: set[str]


class CategoryAgent(agent.Agent):
    '''Data agent for handling item categories.'''
    def __init__(self: CategoryAgent, dataset: DataSet, name: str) -> None:
        super().__init__(dataset, name)
        self._data: CategoryData = CategoryData(
            categories=set()
        )

    @staticmethod
    def _process_data(data: Mapping | Sequence) -> CategoryData:
        if not ismapping(data):
            raise TypeError('Category data must be a mapping.')

        categories = set()
        by_rank = {}

        for rank in types.Rank:
            by_rank[rank] = list(map(make_weighted_entry, data[rank.value]))

            for cat in [x['value'] for x in data[rank.value]]:
                categories.add(cat)

        return CategoryData(
            categories=categories,
            compound=by_rank,
        )

    @log_call_async(logger, 'roll random category')
    async def random(self: CategoryAgent, rank: types.Rank | None = None) -> str | types.Ret:
        match await super().random_compound(rank=rank):
            case types.Ret() as r:
                return r
            case str() as s:
                return s
            case ret:
                logger.warning(bad_return(ret))
                return types.Ret.FAILED

    @log_call_async(logger, 'get categories')
    @types.check_ready(logger)
    async def categories(self: CategoryAgent) -> set[str]:
        '''Return a list of valid categories.'''
        return self._data.categories
