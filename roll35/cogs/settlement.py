# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

from __future__ import annotations

import asyncio
import logging
import random

from typing import TYPE_CHECKING, cast

from nextcord.ext import commands

from .magicitem import roll_many

from ..common import bad_return
from ..data.settlement import SettlementAgent, SettlementEntry, ItemSlots
from ..log import log_call_async
from .. import types

if TYPE_CHECKING:
    from concurrent.futures import Executor

    from ..data import DataSet
    from ..renderer import Renderer

NOT_READY = 'Settlement data is not yet available, please try again later.'

logger = logging.getLogger(__name__)


class Settlement(types.R35Cog):
    '''Roll35 cog for handling settlements.'''
    async def _settlement(self: Settlement, ctx: commands.Context, /, population: int) -> None:
        try:
            pop = int(population)
        except ValueError:
            await ctx.send('Population value must be an integer greater than 0.')
            return

        if pop < 1:
            await ctx.send('Population value must be an integer greater than 0.')
            return

        match await roll_settlement(pop, self.pool, self.ds, self.renderer):
            case (types.Ret.OK, str() as msg):
                await ctx.send(msg)
                return
            case (types.Ret() as ret, str() as msg) if ret is not types.Ret.OK:
                await ctx.send(msg)
                return

        raise RuntimeError

    @commands.command()  # type: ignore
    async def settlement(self, ctx, population: int, /):
        '''Roll magic items for a settlement with the given population.'''
        await self._settlement(ctx, population)


@log_call_async(logger, 'roll settlement items')
async def roll_settlement(population: int, pool: Executor, ds: DataSet, renderer: Renderer, /) -> types.Result[str]:
    '''Roll magic items for a settlement of the given population.'''
    match await cast(SettlementAgent, ds['settlement']).get_by_population_async(population):
        case types.Ret.NOT_READY:
            return (types.Ret.NOT_READY, NOT_READY)
        case SettlementEntry() as settlement:
            response = f'Settlement Category: { settlement.name }\n'
            response += f'Each item with a cost { settlement.base } gp or less has a 75% chance of being available, rerolled weekly.\n'

            for rank in types.Rank:
                match cast(ItemSlots, getattr(settlement, rank.value)):
                    case 'all':
                        response += f'\nAll { rank.value } items are available irrespective of cost.\n'
                    case None:
                        response += f'\nNo additional { rank.value } magic items are available.\n'
                    case [low, high]:
                        slots = random.randint(low, high)  # nosec # Not used for crypto purposes
                        response += f'\nThe following { slots } additional { rank.value } items are available irrespective of cost:\n'
                        for item in asyncio.as_completed(roll_many(pool, ds, slots, {'rank': rank, 'mincost': settlement.base + 1})):
                            match await item:
                                case (types.Ret.OK, types.item.BaseItem() as i1):
                                    match await renderer.render(pool, i1):
                                        case (types.Ret.OK, str() as msg):
                                            response += f'- { msg }\n'
                                        case (types.Ret() as r1, str() as msg) if r1 is not types.Ret.OK:
                                            return (types.Ret.FAILED, f'Failed to generate items for settlement: { msg }')
                                        case r2:
                                            logger.error(bad_return(r2))
                                            return (types.Ret.FAILED, 'Failed to generate items for settlement.')
                                case (types.Ret() as r3, str() as msg) if r3 is not types.Ret.OK:
                                    return (types.Ret.FAILED, f'Failed to generate items for settlement: { msg }')
                                case r4:
                                    logger.error(bad_return(r4))
                                    return (types.Ret.FAILED, 'Failed to generate items for settlement.')

            return (types.Ret.OK, response)
        case ret:
            logger.error(bad_return(ret))
            return (types.Ret.FAILED, 'Unknown internal error.')
