#!python
#
# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

import asyncio
import concurrent.futures
import logging
import logging.config
import os
import sys

from concurrent.futures import ProcessPoolExecutor

import nextcord

from nextcord.ext import commands

from .common import prepare_cog, did_you_mean
from .renderer import Renderer
from . import COGS, BOT_HELP

TOKEN = os.environ['DISCORD_TOKEN']

POOL = ProcessPoolExecutor()

if 'LOG_LEVEL' in os.environ:
    LOG_LEVEL = os.environ['LOG_LEVEL']
else:
    LOG_LEVEL = 'INFO'

logging.config.dictConfig({
    'version': 1,
    'formatters': {
        'basic': {
            'format': '%(asctime)s %(levelname)-8s %(name)-15s %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'basic',
            'level': LOG_LEVEL,
        },
    },
    'root': {
        'handlers': [
            'console'
        ],
        'level': LOG_LEVEL,
    },
    'disable_existing_loggers': False,
})
logging.basicConfig(level=logging.INFO)

logger = logging.getLogger('roll35')


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
            loop = asyncio.get_running_loop()

            match await loop.run_in_executor(
                POOL,
                did_you_mean,
                [x.name for x in self.walk_commands()],
                exception.command_name,
                True,
            ):
                case (True, msg):
                    return await ctx.send(f'{ exception.command_name } is not a recognized command. { msg }')
                case (False, _):
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
        description=BOT_HELP,
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


if __name__ == '__main__':
    main(TOKEN)
