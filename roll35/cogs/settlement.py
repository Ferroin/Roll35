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
from ..data.settlement import SettlementAgent, SettlementEntry
from ..log import log_call_async
from ..types import R35Cog, Rank, Ret, Result

if TYPE_CHECKING:
    from ..data import DataSet
    from ..renderer import Renderer

NOT_READY = 'Settlement data is not yet available, please try again later.'

logger = logging.getLogger(__name__)


class Settlement(R35Cog):
    '''Roll35 cog for handling settlements.'''
    async def _settlement(self: Settlement, ctx: commands.ctx, /, population: int) -> None:
        try:
            pop = int(population)
        except ValueError:
            await ctx.send('Population value must be an integer greater than 0.')
            return

        if pop < 1:
            await ctx.send('Population value must be an integer greater than 0.')
            return

        match await roll_settlement(pop, self.ds, self.renderer):
            case (Ret.OK, msg):
                await ctx.send(msg)
            case (ret, msg) if ret is not Ret.OK:
                await ctx.send(msg)

    @commands.command()
    async def settlement(self, ctx, population: int, /):
        '''Roll magic items for a settlement with the given population.'''
        await self._settlement(ctx, population)


@log_call_async(logger, 'roll settlement items')
async def roll_settlement(population: int, ds: DataSet, renderer: Renderer, /) -> Result[str]:
    '''Roll magic items for a settlement of the given population.'''
    match await cast(SettlementAgent, ds['settlement']).get_by_population(population):
        case Ret.NOT_READY:
            return (Ret.NOT_READY, NOT_READY)
        case SettlementEntry() as settlement:
            response = f'Settlement Category: { settlement.name }\n'
            response += f'Each item with a cost { settlement.base } gp or less has a 75% chance of being available, rerolled weekly.\n'

            for rank in Rank:
                match getattr(settlement, rank.value):
                    case 'all':
                        response += f'\nAll { rank.value } items are available irrespective of cost.\n'
                    case None:
                        response += f'\nNo additional { rank.value } magic items are available.\n'
                    case [low, high]:
                        slots = random.randint(low, high)
                        response += f'\nThe following { slots } additional { rank.value } items are available irrespective of cost:\n'
                        for item in asyncio.as_completed(roll_many(ds, slots, {'rank': rank, 'mincost': settlement.base + 1})):
                            match await item:
                                case (Ret.OK, item):
                                    match await renderer.render(item):
                                        case (Ret.OK, msg):
                                            response += f'- { msg }\n'
                                        case (ret, msg) if ret is not Ret.OK:
                                            return (Ret.FAILED, f'Failed to generate items for settlement: { msg }')
                                        case ret:
                                            logger.error(bad_return(ret))
                                            return (Ret.FAILED, 'Failed to generate items for settlement.')
                                case (ret, msg) if ret is not Ret.OK:
                                    return (Ret.FAILED, f'Failed to generate items for settlement: { msg }')
                                case ret:
                                    logger.error(bad_return(ret))
                                    return (Ret.FAILED, 'Failed to generate items for settlement.')

            return (Ret.OK, response)
        case ret:
            logger.error(bad_return(ret))
            return (Ret.FAILED, 'Unknown internal error.')
