'''Cog for handling weapon items.'''

import logging

from nextcord.ext import commands

from .cog import Cog
from .data.weapons import WeaponAgent

NOT_READY = 'Weapon data is not yet available, please try again later.'

logger = logging.getLogger(__name__)


class Weapon(Cog):
    def __init__(self, bot, pool, renderer, logger=logger):
        self.agent = WeaponAgent(pool)

        super().__init__(bot, renderer, logger)

    @commands.command()
    async def weapon(self, ctx, *tags):
        '''Roll a random mundane weapon item.

           Optionally takes a space-separated list of tags to limit what
           weapon items can be returned. To list recognized tags, run
           `/r35 weapontags`'''
        match await self.agent.random_base(tags):
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
        match await self.agent.tags():
            case False:
                await ctx.send(NOT_READY)
            case []:
                await ctx.send('No tags found for weapons.')
            case tags:
                await ctx.send(
                    'The following weapon tags are recognized: ' +
                    f'`{ "`, `".join(sorted(tags)) }`'
                )
