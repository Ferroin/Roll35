#!python
#
# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

'''Core logic for running the module as a Discord bot.

   This handles setup of logging, the data set, the renderer, and the
   bot itself.'''

import asyncio
import concurrent.futures
import logging
import logging.config
import os
import sys

from concurrent.futures import ProcessPoolExecutor

import nextcord

from nextcord.ext import commands

from . import BOT_HELP
from .cogs import COGS
from .common import did_you_mean, bad_return
from .data import DataSet
from .renderer import Renderer
from .retcode import Ret

TOKEN = os.environ['DISCORD_TOKEN']
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')

logging.config.dictConfig({
    'version': 1,
    'formatters': {
        'basic': {
            'format': '%(asctime)s %(levelname)-7s %(name)-20s %(message)s',
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


class Bot(commands.Bot):
    '''Custom bot class.

       This overrides a few specific methods of the base class to get
       desired behavior.'''
    def __init__(self, *args, pool=None, **kwargs):
        self.pool = pool
        super().__init__(*args, **kwargs)

    async def start(self, token, *args, reconnect=True, ds=None, renderer=None):
        '''Overridden to schedule data loads in parallel with bot startup.'''
        return await asyncio.gather(
            ds.load_data(self.pool),
            renderer.load_data(self.pool),
            super().start(token, *args, reconnect=reconnect),
        )

    async def on_command_error(self, ctx, exception):
        '''Overridden to provide useful feedback to users on bad commands.'''
        if isinstance(exception, commands.errors.CommandNotFound):
            loop = asyncio.get_running_loop()

            match await loop.run_in_executor(
                self.pool,
                did_you_mean,
                [x.name for x in self.walk_commands()],
                exception.command_name,
                True,
            ):
                case (Ret.OK, msg):
                    return await ctx.send(f'{ exception.command_name } is not a recognized command. { msg }')
                case (Ret.NO_MATCH, _):
                    return await ctx.send(f'{ exception.command_name } is not a recognized command.')
                case ret:
                    logger.error(bad_return(ret))
                    return await ctx.send(f'{ exception.command_name } is not a recognized command.')

        await super().on_command_error(ctx, exception)

    async def on_error(self, event_method, *args, **kwargs):
        '''Overridden to explicitly bail on specific error types.'''
        match sys.exc_info():
            case (concurrent.futures.BrokenExecutor, _, _):
                raise
            case _:
                await super().on_error(event_method, *args, **kwargs)


def main(token):
    intents = nextcord.Intents.default()
    intents.message_content = True
    pool = ProcessPoolExecutor()

    bot = Bot(
        case_insensitive=True,
        command_prefix=[
            '/r35 ',
            '/R35 ',
        ],
        description=BOT_HELP,
        intents=intents,
        strip_after_prefix=True,
        pool=pool,
    )
    ds = DataSet()
    renderer = Renderer(ds)

    @bot.event
    async def on_ready():
        logger.info(f'Successfully logged in as { bot.user }')

    logger.info('Loading cogs.')

    for entry in COGS:
        cog = entry(bot, ds, renderer)
        bot.add_cog(cog)

    logger.info(f'Starting bot with token: { token }')

    try:
        bot.run(TOKEN, ds=ds, renderer=renderer)
    finally:
        pool.shutdown(cancel_futures=True)


if __name__ == '__main__':
    main(TOKEN)
