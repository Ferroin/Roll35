# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

'''Cog for handling settlements.'''

import asyncio
import logging
import random

from nextcord.ext import commands

from .cog import Cog
from .retcode import Ret
from .data.constants import RANK
from .magicitem import roll_many

NOT_READY = 'Settlement data is not yet available, please try again later.'

logger = logging.getLogger(__name__)


class Settlement(Cog):
    def __init__(self, bot, ds, renderer, logger=logger):
        super().__init__(bot, ds, renderer, logger)

    @commands.command()
    async def settlement(self, ctx, population):
        '''Roll magic items for a settlement with the given population.'''
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


async def roll_settlement(population, ds, renderer):
    '''Roll magic items for a settlement of the given population.'''
    settlement = await ds['settlement'].get_by_population(population)

    if not settlement:
        return (Ret.NOT_READY, NOT_READY)

    response = f'Settlement Category: { settlement["name"] }\n'
    response += f'Each item with a cost { settlement["base"] } gp or less has a 75% chance of being available, rerolled weekly.\n'

    for rank in RANK:
        match settlement[rank]:
            case 'all':
                response += f'\nAll { rank } items are available irrespective of cost.\n'
            case None:
                response += f'\nNo additional { rank } magic items are available.\n'
            case [low, high]:
                slots = random.randint(low, high)
                response += f'\nThe following { slots } additional { rank } items are available irrespective of cost:\n'
                for item in asyncio.as_completed(roll_many(ds, slots, {'rank': rank, 'mincost': settlement['base']})):
                    match await item:
                        case (Ret.OK, item):
                            match await renderer.render(item):
                                case (Ret.OK, msg):
                                    response += f'- { msg }\n'
                                case (ret, msg) if ret is not Ret.OK:
                                    return (Ret.FAILED, f'Failed to generate items for settlement: { msg }')
                        case (ret, msg) if ret is not Ret.OK:
                            return (Ret.FAILED, f'Failed to generate items for settlement: { msg }')

    return (Ret.OK, response)
