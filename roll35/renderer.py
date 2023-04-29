# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

'''Render a message properly.'''

import asyncio
import logging

import jinja2

from .common import check_ready, bad_return
from .retcode import Ret

logger = logging.getLogger(__name__)

MAX_TEMPLATE_RECURSION = 5


class Renderer:
    '''Encapsulates the state required for rendering items.'''
    def __init__(self, dataset):
        self.env = jinja2.Environment(
            loader=jinja2.FunctionLoader(lambda x: None),
            autoescape=False,
            enable_async=True,
        )

        self._data = None
        self._ready = asyncio.Event()
        self._ds = dataset

    @staticmethod
    def _loader(name):
        from .common import yaml
        from .data import DATA_ROOT
        from .types import RenderData

        with open(DATA_ROOT / f'{ name }.yaml') as f:
            return RenderData(yaml.load(f))

    async def load_data(self, pool):
        '''Load required data.'''
        if not self._ready.is_set():
            loop = asyncio.get_running_loop()

            logger.info('Loading renderer data.')
            self._data = await loop.run_in_executor(pool, self._loader, self._ds.renderdata)
            logger.info('Finished loading renderer data.')

            self._ready.set()

        return Ret.OK

    async def get_spell(self, item):
        '''Get a random spell for the given item.'''
        match await self._ds['spell'].random(**item['spell']):
            case (Ret.OK, spell):
                return (Ret.OK, spell)
            case (ret, msg) if ret is not Ret.OK:
                return (ret, msg)
            case Ret.NOT_READY:
                return (Ret.NOT_READY, 'Unable to get spell for item.')
            case ret:
                logger.error(bad_return(ret))
                return (Ret.FAILED, 'Unknown internal error.')

    async def render(self, item):
        '''Render an item.

           This recursively evaluates the item name as a jinja2 template,
           possibly with some extra formatting added.

           Returns either (True, x) where x is the rendered item, or
           (False, msg) where msg is an error message.'''
        match await self._render(item):
            case Ret.NOT_READY:
                return (Ret.NOT_READY, 'Unable to render item as renderer is not yet fully initilized.')
            case ret:
                return ret

    @check_ready
    async def _render(self, item):
        match item:
            case {'name': name, 'cls': _, 'caster_level': _, 'level': _}:
                t = '{{ item["name"] }} ({{ item["cls"].capitalize() }} {{ item["level"] }}, CL {{ item["caster_level"] }})'
            case {'name': name, 'cost': _}:
                if '{{ spell }}' in name:
                    t = '{{ item["name"] }} ({{ item["cls"].capitalize() }} {{ item["level"] }}, CL {{ item["caster_level"] }}, {{ item["cost"] }} gp)'
                else:
                    t = '{{ item["name"] }} ({{ item["cost"] }} gp)'
            case {'name': name}:
                if '{{ spell }}' in name:
                    t = '{{ item["name"] }} ({{ item["cls"].capitalize() }} {{ item["level"] }}, CL {{ item["caster_level"] }})'
                else:
                    t = name
            case name if isinstance(name, str):
                item = {'name': item}
                if '{{ spell }}' in name:
                    t = '{{ item["name"] }} ({{ item["cls"].capitalize() }} {{ item["level"] }}, CL {{ item["caster_level"] }})'
                else:
                    t = name
            case _:
                logger.error(f'Failed to render item: { item }.')
                return (Ret.INVALID, 'Failed to render item.')

        n = ''
        i = 0

        while True:
            i += 1

            if i > MAX_TEMPLATE_RECURSION:
                logger.error('Too many levels of recursion in template: { template }.')
                return (Ret.LIMMITED, 'Failed to render item.')

            if 'spell' in item:
                if 'rolled_spell' in item:
                    spell = item['rolled_spell']['name']
                    item['cls'] = item['rolled_spell']['cls']
                    item['caster_level'] = item['rolled_spell']['caster_level']
                    item['level'] = item['rolled_spell']['level']
                else:
                    match await self.get_spell(item):
                        case (Ret.OK, spell):
                            item['cls'] = spell['cls']
                            item['caster_level'] = spell['caster_level']
                            spell = spell['name']
                        case (ret, msg) if ret is not Ret.OK:
                            return (ret, msg)
                        case ret:
                            logger.error(bad_return(ret))
                            return (Ret.FAILED, 'Unknown internal error.')
            else:
                spell = None

            n = await self.env.from_string(t).render_async({'keys': self._data, 'spell': spell, 'item': item})

            if n == t:
                return (Ret.OK, n)
            else:
                t = n
