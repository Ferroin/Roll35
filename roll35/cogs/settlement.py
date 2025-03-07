# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

'''Cog for rolling items for settlements.'''

from __future__ import annotations

import asyncio
import logging

from nextcord.ext import commands

from .. import types
from ..common import bad_return
from ..roller.settlement import SettlementItems, roll_settlement_async

logger = logging.getLogger(__name__)


class Settlement(types.R35Cog):
    '''Roll35 cog for handling settlements.'''
    async def __settlement(self: Settlement, ctx: commands.Context, /, population: int) -> None:
        try:
            pop = int(population)
        except ValueError:
            await ctx.send('Population value must be an integer greater than 0.')
            return

        if pop < 1:
            await ctx.send('Population value must be an integer greater than 0.')
            return

        match await roll_settlement_async(pop, self.pool, self.ds, self.renderer):
            case (types.Ret.OK, SettlementItems() as data):
                response = f'Settlement Category: {data.category}\n'
                response += f'Each item with a cost {data.base} gp or less has a 75% chance of being available, rerolled weekly.\n'

                for rank in types.Rank:
                    match data.items[rank]:
                        case 'all':
                            response += f'\nAll {rank.value} items are available irrespective of cost.\n'
                        case None:
                            response += f'\nNo additional {rank.value} magic items are available.\n'
                        case items if items is not None and not isinstance(items, str):
                            response += f'\nThe following {len(items)} additional {rank.value} items are available irrespective of cost:\n'

                            for item in asyncio.as_completed(items):
                                match await item:
                                    case (types.Ret.OK, types.item.BaseItem() as i1):
                                        match await self.render(i1):
                                            case (types.Ret.OK, str() as msg):
                                                response += f'- {msg}\n'
                                            case (types.Ret() as r1, str() as msg) if r1 is not types.Ret.OK:
                                                await ctx.send(f'Failed to generate items for settlement: {msg}')
                                                return
                                            case r2:
                                                logger.error(bad_return(r2))
                                                await ctx.send('Failed to generate items for settlement.')
                                                return
                                    case (types.Ret() as r3, str() as msg) if r3 is not types.Ret.OK:
                                        await ctx.send(f'Failed to generate items for settlement: {msg}')
                                        return
                                    case r4:
                                        logger.error(bad_return(r4))
                                        await ctx.send('Failed to generate items for settlement.')
                                        return

                await ctx.send(response)
                return
            case (types.Ret() as ret, str() as msg) if ret is not types.Ret.OK:
                await ctx.send(msg)
                return

    @commands.command()
    async def settlement(self, ctx, population: int, /):
        '''Roll magic items for a settlement with the given population.'''
        await self.__settlement(ctx, population)
