# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

'''Render a message properly.'''

from __future__ import annotations

import asyncio
import logging

from typing import TYPE_CHECKING, cast

import jinja2

from . import types
from .common import check_ready, bad_return
from .data.spell import SpellAgent
from .types.renderdata import RenderData
from .log import LogRun, log_call_async

if TYPE_CHECKING:
    from concurrent.futures import Executor

    from .data import DataSet

logger = logging.getLogger(__name__)

MAX_TEMPLATE_RECURSION = 5


class Renderer:
    '''Encapsulates the state required for rendering items.'''
    def __init__(self: Renderer, dataset: DataSet) -> None:
        self.env = jinja2.Environment(
            loader=jinja2.FunctionLoader(lambda x: None),
            autoescape=False,
            enable_async=True,
        )

        self._data: RenderData = RenderData(dict())
        self._ready = asyncio.Event()
        self._ds = dataset

    @staticmethod
    def _loader(name: str) -> RenderData:
        from .common import yaml
        from .data import DATA_ROOT

        with open(DATA_ROOT / f'{ name }.yaml') as f:
            return RenderData(yaml.load(f))

    async def load_data(self: Renderer, pool: Executor) -> types.Ret:
        '''Load required data.'''
        if not self._ready.is_set():
            loop = asyncio.get_running_loop()

            with LogRun(logger, logging.INFO, 'load renderer data'):
                self._data = await loop.run_in_executor(pool, self._loader, self._ds.renderdata)

            self._ready.set()

        return types.Ret.OK

    async def get_spell(self: Renderer, item: types.item.SpellItem) -> types.Result[types.item.SpellEntry]:
        '''Get a random spell for the given item.'''
        match await cast(SpellAgent, self._ds['spell']).random(**item.spell):
            case (types.Ret.OK, spell):
                return (types.Ret.OK, spell)
            case (ret, msg) if ret is not types.Ret.OK:
                return (ret, msg)
            case types.Ret.NOT_READY:
                return (types.Ret.NOT_READY, 'Unable to get spell for item.')
            case ret:
                logger.error(bad_return(ret))
                return (types.Ret.FAILED, 'Unknown internal error.')

    @log_call_async(logger, 'render item')
    async def render(self: Renderer, item: types.item.Item | types.item.SpellEntry | str) -> types.Result[str]:
        '''Render an item.

           This recursively evaluates the item name as a jinja2 template,
           possibly with some extra formatting added.

           Returns either (roll35.retcode.Ret.OK, x) where x is the rendered item, or
           (roll35.retcode.Ret.*, msg) where msg is an error message.'''
        match await self._render(item):
            case types.Ret.NOT_READY:
                return (types.Ret.NOT_READY, 'Unable to render item as renderer is not yet fully initilized.')
            case ret:
                return ret

    @check_ready
    async def _render(self: Renderer, item: types.item.Item | types.item.SpellEntry | str) -> types.Result[str]:
        match item:
            case types.item.SpellEntry(name=name, cls=c, caster_level=cl, level=l) if c is not None and cl is not None and l is not None:
                t = '{{ item.name }} ({{ item.cls.capitalize() }} {{ item.level }}, CL {{ item.caster_level }})'
            case types.item.SimpleItem(name=name, cost=cost) if cost is not None:
                if '{{ spell }}' in name:
                    t = '{{ item.name }} ({{ item.cls.capitalize() }} {{ item.level }}, CL {{ item.caster_level }}, {{ item.cost }} gp)'
                else:
                    t = '{{ item.name }} ({{ item.cost }} gp)'
            case types.item.SimpleItem(name=name):
                if '{{ spell }}' in name:
                    t = '{{ item.name }} ({{ item.cls.capitalize() }} {{ item.level }}, CL {{ item.caster_level }})'
                else:
                    t = name
            case str() as name:
                item = types.item.SimpleItem(
                    name=name
                )
                if '{{ spell }}' in name:
                    t = '{{ item.name }} ({{ item.cls.capitalize() }} {{ item.level }}, CL {{ item.caster_level }})'
                else:
                    t = name
            case _:
                logger.error(f'Failed to render item: { item }.')
                return (types.Ret.INVALID, 'Failed to render item.')

        n = ''
        i = 0

        while True:
            i += 1

            if i > MAX_TEMPLATE_RECURSION:
                logger.error('Too many levels of recursion in template: { template }.')
                return (types.Ret.LIMITED, 'Failed to render item.')

            if isinstance(item, types.item.SpellItem):
                if item.rolled_spell is not None:
                    spell = item.rolled_spell.name
                    item.cls = item.rolled_spell.cls
                    item.caster_level = item.rolled_spell.caster_level
                    item.level = item.rolled_spell.level
                else:
                    match await self.get_spell(item):
                        case (types.Ret.OK, types.item.SpellEntry() as s):
                            item.cls = s.cls
                            item.caster_level = s.caster_level
                            item.level = s.level
                            spell = s.name
                        case (types.Ret.NOT_READY, str() as msg):
                            return (types.Ret.NOT_READY, msg)
                        case ret:
                            logger.error(bad_return(ret))
                            return (types.Ret.FAILED, 'Unknown internal error.')
            else:
                spell = None

            n = await self.env.from_string(t).render_async({'keys': self._data, 'spell': spell, 'item': item})

            if n == t:
                return (types.Ret.OK, n)
            else:
                t = n
