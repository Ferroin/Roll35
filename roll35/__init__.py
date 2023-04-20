import asyncio
import concurrent.futures
import logging
import os
import sys

from concurrent.futures import ProcessPoolExecutor

import nextcord

from nextcord.ext import commands

from .common import prepare_cog, PREFIX

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
    async def on_error(event_method, *args, **kwargs):
        match sys.exc_info():
            case (concurrent.futures.BrokenExecutor, _, _):
                raise
            case _:
                await super().on_error(event_method, *args, **kwargs)


def main(token):
    intents = nextcord.Intents.default()
    intents.message_content = True

    bot = Bot(command_prefix=PREFIX + ' ', intents=intents)
    renderer = Renderer(POOL, bot)

    @bot.event
    async def on_ready():
        logger.info(f'Successfully logged in as { bot.user }')

    @bot.event
    async def on_connect():
        await register_cogs(bot, renderer)

    logger.info(f'Starting bot with token: { token }')
    bot.run(token)
