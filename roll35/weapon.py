# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

'''Cog for handling weapon items.'''

import logging

from nextcord.ext import commands

from .cog import Cog

NOT_READY = 'Weapon data is not yet available, please try again later.'

logger = logging.getLogger(__name__)


class Weapon(Cog):
    def __init__(self, bot, ds, renderer, logger=logger):
        super().__init__(bot, ds, renderer, logger)

    @commands.command()
    async def weapon(self, ctx, *tags):
        '''Roll a random mundane weapon item.

           Optionally takes a space-separated list of tags to limit what
           weapon items can be returned. To list recognized tags, run
           `/r35 weapontags`'''
        match await self.ds['weapon'].random_base(tags):
            case False:
                await ctx.send(NOT_READY)
            case None:
                await ctx.send('No item found matching requested tags.')
            case item:
                match await self.render(item):
                    case (True, msg):
                        await ctx.send(msg)
                    case (False, msg):
                        await ctx.send(msg)

    @commands.command()
    async def weapontags(self, ctx):
        '''List known weapon tags.'''
        match await self.ds['weapon'].tags():
            case False:
                await ctx.send(NOT_READY)
            case []:
                await ctx.send('No tags found for weapons.')
            case tags:
                await ctx.send(
                    'The following weapon tags are recognized: ' +
                    f'`{ "`, `".join(sorted(tags)) }`'
                )
