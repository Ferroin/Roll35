# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

'''Render a message properly.'''

from __future__ import annotations

import asyncio
import logging

from typing import TYPE_CHECKING, Literal, cast

import jinja2

from . import types
from .common import yaml, ismapping
from .types.renderdata import RenderData
from .types.readystate import ReadyState, check_ready_async
from .log import log_call_async

if TYPE_CHECKING:
    from concurrent.futures import Executor
    from collections.abc import Mapping, Sequence

    from .data import DataSet

logger = logging.getLogger(__name__)

MAX_TEMPLATE_RECURSION = 5


class Renderer(ReadyState):
    '''Encapsulates the state required for rendering items.'''
    def __init__(self: Renderer, /, dataset: DataSet) -> None:
        self._data: RenderData = RenderData(dict())
        self._ds = dataset

        super().__init__()

    @staticmethod
    def _process_data(data: Mapping | Sequence, /) -> RenderData:
        if not ismapping(data):
            raise ValueError('Renderer data must be a mapping')

        return RenderData(data)

    async def load_data(self: Renderer, pool: Executor, /) -> types.Ret:
        '''Load required data.'''
        if not self._ready.is_set():
            loop = asyncio.get_running_loop()
            logger.info('Loading renderer data')

            with open(self._ds.src / f'{ self._ds.renderdata }.yaml') as f:
                data = yaml.load(f)

            self._data = await loop.run_in_executor(pool, self._process_data, data)

            logger.info('Finished loading renderer data')

            self._ready.set()

        return types.Ret.OK

    @log_call_async(logger, 'render item')
    async def render(self: Renderer, pool: Executor, /, item: types.item.BaseItem | types.item.Spell | str) -> types.Result[str]:
        '''Render an item.

           This recursively evaluates the item name as a jinja2 template,
           possibly with some extra formatting added.

           Returns either (roll35.retcode.Ret.OK, x) where x is the rendered item, or
           (roll35.retcode.Ret.*, msg) where msg is an error message.'''
        match await self._render(pool, item):
            case types.Ret.NOT_READY:
                return (types.Ret.NOT_READY, 'Unable to render item as renderer is not yet fully initilized.')
            case r2:
                return cast(types.Result[str], r2)

    @staticmethod
    def render_loop(tmpl: str, data: DataSet, item: types.item.BaseItem) -> types.Result[str]:
        n = ''
        i = 0

        env = jinja2.Environment(
            loader=jinja2.FunctionLoader(lambda x: None),
            autoescape=True,
        )

        while True:
            i += 1

            if i > MAX_TEMPLATE_RECURSION:
                logger.error('Too many levels of recursion in template: { template }.')
                return (types.Ret.LIMITED, 'Failed to render item.')

            if isinstance(item, types.item.SpellItem):
                if item.rolled_spell is not None:
                    spell = item.rolled_spell.name
                    item.cls = item.rolled_spell.rolled_cls
                    if item.cls is None:
                        raise RuntimeError
                    item.caster_level = item.rolled_spell.rolled_caster_level
                    item.level = item.rolled_spell.classes[item.cls]
                else:
                    logger.error('Got a SpellItem without a rolled spell: { item }.')
                    return (types.Ret.FAILED, 'Failed to render item.')

            else:
                spell = None

            n = env.from_string(tmpl).render({'keys': data, 'spell': spell, 'item': item})

            if n == tmpl:
                return (types.Ret.OK, n)
            else:
                tmpl = n

    @check_ready_async(logger)
    async def _render(self: Renderer, pool: Executor, /, item: types.item.BaseItem | types.item.Spell | str) -> \
            types.Result[str] | Literal[types.Ret.NOT_READY]:
        match item:
            case types.item.Spell(name=name, rolled_cls=c, rolled_caster_level=cl) if c is not None and cl is not None:
                t = '{{ item.name }} ({{ item.rolled_cls.capitalize() }} {{ item.classes[item.rolled_cls] }}, CL {{ item.rolled_caster_level }})'
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

        loop = asyncio.get_running_loop()

        return await loop.run_in_executor(pool, self.render_loop, t, self._data, item)
