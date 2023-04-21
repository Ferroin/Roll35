import asyncio
import concurrent.futures
import logging
import sys

from concurrent.futures import ProcessPoolExecutor

import nextcord

from nextcord.ext import commands

from .common import prepare_cog

from .core import Core
from .spell import Spell
from .magicitem import MagicItem
from .armor import Armor
from .weapon import Weapon

from .renderer import Renderer

COGS = [
    Core,
    Spell,
    MagicItem,
    Armor,
    Weapon,
]

POOL = ProcessPoolExecutor()

DESCRIPTION = '''Roll items and spells for first-edition Pathfinder.

Note that currently we do not support:

- Rolling random materials for magic armor and weapons.
- Rolling stored spells for items capable of storing spells.
- Rolling for whether an item is intelligent or not.
- Rolling for whether magic items have special markings or not.
- Rolling skills for items that provide skill ranks.

This bot is capable of responding to direct messages, though you will
still need to use the command prefix.

Supported commands, grouped by category:
'''

logger = logging.getLogger(__name__)


async def register_cogs(bot, renderer):
    '''Register all defined cogs on the specified bot.'''
    loaders = [
        renderer.load_data(),
    ]

    for entry in COGS:
        if not bot.get_cog(entry.qualified_name):
            logger.info(f'Loading Cog: { entry }')
            cog = entry(bot, POOL, renderer)
            loaders.append(prepare_cog(cog))
            bot.add_cog(cog)

    if loaders:
        await asyncio.gather(*loaders)


class Bot(commands.Bot):
    async def on_command_error(self, ctx, exception):
        if isinstance(exception, commands.errors.CommandNotFound):
            return await ctx.send(f'{ exception.command_name } is not a recognized command.')

        await super().on_command_error(ctx, exception)

    async def on_error(self, event_method, *args, **kwargs):
        match sys.exc_info():
            case (concurrent.futures.BrokenExecutor, _, _):
                raise
            case _:
                await super().on_error(event_method, *args, **kwargs)


def main(token):
    intents = nextcord.Intents.default()
    intents.message_content = True

    bot = Bot(
        case_insensitive=True,
        command_prefix=[
            '/r35 ',
            '/R35 ',
        ],
        description=DESCRIPTION,
        intents=intents,
        strip_after_prefix=True,
    )
    renderer = Renderer(POOL, bot)

    @bot.event
    async def on_ready():
        logger.info(f'Successfully logged in as { bot.user }')

    @bot.event
    async def on_connect():
        await register_cogs(bot, renderer)

    logger.info(f'Starting bot with token: { token }')
    bot.run(token)
