# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

'''Cog for handling armor and weapon items.'''

from nextcord.ext import commands

from ..retcode import Ret
from ..types import R35Cog

NOT_READY = 'Item data is not yet available, please try again later.'


class Ordnance(R35Cog):
    async def get_item(self, ctx, typ, *tags):
        '''Get a mundane item.'''
        match await self.ds[typ].random_base(tags):
            case Ret.NOT_READY:
                await ctx.send(NOT_READY)
            case Ret.NO_MATCH:
                await ctx.send('No item found matching requested tags.')
            case item:
                _ret, msg = await self.renderer.render(item)
                await ctx.send(msg)

    async def get_tags(self, ctx, typ):
        match await self.ds[typ].tags():
            case Ret.NOT_READY:
                await ctx.send(NOT_READY)
            case Ret.NO_MATCH:
                await ctx.send('No tags found.')
            case tags:
                await ctx.send(
                    f'The following { typ } tags are recognized: ' +
                    f'`{ "`, `".join(sorted(tags)) }`'
                )

    @commands.command()
    async def armor(self, ctx, *tags):
        '''Roll a random mundane armor item.

           Optionally takes a space-separated list of tags to limit what
           armor items can be returned. To list recognized tags, run
           `/r35 armortags`.'''
        await self.get_item(ctx, 'armor', *tags)

    @commands.command()
    async def armortags(self, ctx):
        '''List known armor tags.'''
        await self.get_tags(ctx, 'armor')

    @commands.command()
    async def weapon(self, ctx, *tags):
        '''Roll a random mundane weapon item.

           Optionally takes a space-separated list of tags to limit what
           weapon items can be returned. To list recognized tags, run
           `/r35 weapontags`'''
        await self.get_item(ctx, 'weapon', *tags)

    @commands.command()
    async def weapontags(self, ctx):
        '''List known weapon tags.'''
        await self.get_tags(ctx, 'weapon')
