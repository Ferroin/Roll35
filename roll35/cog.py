'''Base class for all of our cogs.'''

import logging

from nextcord.ext import commands

logger = logging.getLogger(__name__)


class Cog(commands.Cog):
    def __init__(self, bot, renderer, logger=logger):
        self.bot = bot
        self.renderer = renderer
        self.logger = logger

    async def render(self, item):
        return await self.renderer.render(item)

    async def load_agent_data(self):
        if hasattr(self, 'agent'):
            await self.agent.load_data()
        else:
            pass

    async def cog_before_invoke(self, ctx):
        await ctx.trigger_typing()

        self.logger.debug(
            f'Invoking { ctx.command.name } from message { ctx.message.content }.'
        )

    async def cog_command_error(self, ctx, err):
        await ctx.send(
            'Error encountered while processing command:\n' + repr(err)
        )
        raise
