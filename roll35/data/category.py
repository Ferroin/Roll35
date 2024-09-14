# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

'''Data handling for item categories.'''

from __future__ import annotations

import logging

from dataclasses import dataclass
from typing import TYPE_CHECKING

from . import agent
from .. import types
from ..common import bad_return, ismapping, make_weighted_entry
from ..log import log_call, log_call_async

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence

    from . import DataSet

logger = logging.getLogger(__name__)


def process_category_list(items: Iterable[types.CompoundItem], /) -> types.CompoundItemList:
    '''Process a compound list of weighted values.

       Each list entry must be a dict with keys coresponding to the
       possible values for `roll35.types.Rank` with each such key bearing
       a weight to use for the entry when rolling a random item of the
       corresponding rank.'''
    ret: types.CompoundItemList = types.R35Map()

    for rank in types.Rank:
        ilist: types.CompoundItemSublist = types.R35List()

        for item in items:
            if getattr(item, rank.value):
                item.weight = getattr(item, rank.value)
                ilist.append(make_weighted_entry(
                    item,
                ))

        ret[rank] = ilist

    return ret


@dataclass
class CategoryData(agent.AgentData):
    '''Data managed by a CategoryAgent.'''
    categories: set[str]


class CategoryAgent(agent.Agent):
    '''Data agent for handling item categories.'''
    def __init__(self: CategoryAgent, dataset: DataSet, name: str, /) -> None:
        super().__init__(dataset, name)
        self._data: CategoryData = CategoryData(
            categories=set()
        )

    @staticmethod
    def _process_data(data: Mapping | Sequence, /) -> CategoryData:
        if not ismapping(data):
            raise TypeError('Category data must be a mapping.')

        by_name = {}

        for rank in types.Rank:
            for item in data[rank.value]:
                if item['value'] not in by_name:
                    by_name[item['value']] = types.CompoundItem(name=item['value'])

                setattr(by_name[item['value']], rank.value, item['weight'])

        return CategoryData(
            categories={x for x in by_name.keys()},
            compound=process_category_list(by_name.values()),
        )

    def _post_validate(self: CategoryAgent, data: CategoryData) -> bool:  # type: ignore[override]
        for category in data.categories:
            if category not in self._ds:
                raise ValueError(f'Category {category} does not have an associated agent.')

        return True

    @log_call(logger, 'roll random category')
    def random(self: CategoryAgent, /, rank: types.Rank | None = None) -> str | types.Ret:
        match super().random_compound(rank=rank):
            case types.Ret() as r:
                return r
            case types.CompoundItem() as s:
                return s.name
            case ret:
                logger.warning(bad_return(ret))
                return types.Ret.FAILED

    @log_call_async(logger, 'roll random category')
    async def random_async(self: CategoryAgent, /, rank: types.Rank | None = None) -> str | types.Ret:
        match await super().random_compound_async(rank=rank):
            case types.Ret() as r:
                return r
            case types.CompoundItem() as s:
                return s.name
            case ret:
                logger.warning(bad_return(ret))
                return types.Ret.FAILED

    @log_call(logger, 'get categories')
    @types.check_ready(logger)
    def categories(self: CategoryAgent, /) -> set[str]:
        '''Return a list of valid categories.'''
        return self._data.categories

    @log_call_async(logger, 'get categories')
    @types.check_ready_async(logger)
    async def categories_async(self: CategoryAgent, /) -> set[str]:
        '''Return a list of valid categories.'''
        return self._data.categories
