# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

'''Cog for handling armor items.'''

import logging

from nextcord.ext import commands

from .cog import Cog

NOT_READY = 'Armor data is not yet available, please try again later.'

logger = logging.getLogger(__name__)


class Armor(Cog):
    def __init__(self, bot, ds, renderer, logger=logger):
        super().__init__(bot, ds, renderer, logger)

    @commands.command()
    async def armor(self, ctx, *tags):
        '''Roll a random mundane armor item.

           Optionally takes a space-separated list of tags to limit what
           armor items can be returned. To list recognized tags, run
           `/r35 armortags`.'''
        match await self.ds['armor'].random_base(tags):
            case False:
                await ctx.send(NOT_READY)
            case None:
                await ctx.send('No item found matching requested tags.')
            case item:
                match await self.renderer.render(item):
                    case (True, msg):
                        await ctx.send(msg)
                    case (False, msg):
                        await ctx.send(msg)

    @commands.command()
    async def armortags(self, ctx):
        '''List known armor tags.'''
        match await self.ds['armor'].tags():
            case False:
                await ctx.send(NOT_READY)
            case []:
                await ctx.send('No tags found for armor or shields.')
            case tags:
                await ctx.send(
                    'The following armor tags are recognized: ' +
                    f'`{ "`, `".join(sorted(tags)) }`'
                )
