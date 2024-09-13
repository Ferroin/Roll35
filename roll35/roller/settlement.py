# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

'''Functions for rolling magic items for settlements.'''

from __future__ import annotations

import logging
import random

from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from .magicitem import roll_many_async
from .. import types
from ..common import bad_return
from ..data.settlement import ItemSlots, SettlementAgent, SettlementEntry
from ..log import log_call_async

if TYPE_CHECKING:
    from collections.abc import Awaitable, MutableMapping, Sequence
    from concurrent.futures import Executor

    from ..data import DataSet
    from ..renderer import Renderer

NOT_READY = 'Settlement data is not yet available, please try again later.'

logger = logging.getLogger(__name__)


@dataclass
class SettlementItems:
    '''A dataclass representing magic items for a settlement.'''
    category: str
    base: int | float
    items: MutableMapping[types.Rank, Sequence[Awaitable[types.Result[types.item.BaseItem]]] | None | str]


@log_call_async(logger, 'roll settlement items')
async def roll_settlement_async(population: int, pool: Executor, ds: DataSet, renderer: Renderer, /) -> types.Result[SettlementItems]:
    '''Roll magic items for a settlement of the given population.'''
    match await cast(SettlementAgent, ds['settlement']).get_by_population_async(population):
        case types.Ret.NOT_READY:
            return (types.Ret.NOT_READY, NOT_READY)
        case SettlementEntry() as settlement:
            items: dict[types.Rank, str | None | Sequence[Awaitable[types.Result[types.item.BaseItem]]]] = dict()

            for rank in types.Rank:
                match cast(ItemSlots, getattr(settlement, rank.value)):
                    case 'all':
                        items[rank] = 'all'
                    case None:
                        items[rank] = None
                    case [low, high]:
                        slots = random.randint(low, high)  # nosec # Not used for crypto purposes
                        items[rank] = roll_many_async(pool, ds, slots, {'rank': rank, 'mincost': settlement.base + 1})

            return (types.Ret.OK, SettlementItems(
                category=settlement.name,
                base=settlement.base,
                items=items,
            ))
        case ret:
            logger.error(bad_return(ret))
            return (types.Ret.FAILED, 'Unknown internal error.')
