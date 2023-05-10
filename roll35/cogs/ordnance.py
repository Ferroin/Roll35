# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

from __future__ import annotations

import logging

from typing import TYPE_CHECKING, cast

from nextcord.ext import commands

from ..common import bad_return
from ..types import R35Cog, Ret
from ..types.item import OrdnanceBaseItem
from ..data.ordnance import OrdnanceAgent

if TYPE_CHECKING:
    from collections.abc import Sequence

logger = logging.getLogger(__name__)

NOT_READY = 'Item data is not yet available, please try again later.'


class Ordnance(R35Cog):
    '''Roll35 cog for handling mundane armor and weapons.'''
    async def get_item(self: Ordnance, ctx: commands.Context, typ: str, /, tags: Sequence[str]) -> None:
        '''Get a mundane item.'''
        match await cast(OrdnanceAgent, self.ds[typ]).random_base(tags):
            case Ret.NOT_READY:
                await ctx.send(NOT_READY)
            case Ret.NO_MATCH:
                await ctx.send('No item found matching requested tags.')
            case OrdnanceBaseItem() as item:
                _ret, msg = await self.renderer.render(item)
                await ctx.send(msg)
            case ret:
                logger.warning(bad_return(ret))
                await ctx.send('Unknown internal error.')

    async def get_tags(self: Ordnance, ctx: commands.Context, typ: str, /) -> None:
        match await cast(OrdnanceAgent, self.ds[typ]).tags():
            case Ret.NOT_READY:
                await ctx.send(NOT_READY)
            case Ret.NO_MATCH:
                await ctx.send('No tags found.')
            case list() as tags:
                await ctx.send(
                    f'The following { typ } tags are recognized: ' +
                    f'`{ "`, `".join(sorted(tags)) }`'
                )
            case ret:
                logger.warning(bad_return(ret))
                await ctx.send('Unknown internal error.')

    @commands.command()
    async def armor(self, ctx, *tags):
        '''Roll a random mundane armor item.

           Optionally takes a space-separated list of tags to limit what
           armor items can be returned. To list recognized tags, run
           `/r35 armortags`.'''
        await self.get_item(ctx, 'armor', tags)

    @commands.command()
    async def armortags(self, ctx, /):
        '''List known armor tags.'''
        await self.get_tags(ctx, 'armor')

    @commands.command()
    async def weapon(self, ctx, *tags):
        '''Roll a random mundane weapon item.

           Optionally takes a space-separated list of tags to limit what
           weapon items can be returned. To list recognized tags, run
           `/r35 weapontags`'''
        await self.get_item(ctx, 'weapon', tags)

    @commands.command()
    async def weapontags(self, ctx, /):
        '''List known weapon tags.'''
        await self.get_tags(ctx, 'weapon')
