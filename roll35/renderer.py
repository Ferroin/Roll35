# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

'''Render a message properly.'''

import asyncio
import logging

import jinja2

from .common import check_ready, expand_weighted_list, yaml, rnd
from .data import DATA_ROOT

logger = logging.getLogger(__name__)

MAX_TEMPLATE_RECURSION = 5


class RenderData:
    '''Data used to render templates.'''
    def __init__(self, data, logger=logger):
        self._data = data
        self.logger = logger

    def __getitem__(self, key):
        match self._data[key]:
            case {'type': 'grouped_proportional', 'data': data}:
                ret = dict()

                for group in data:
                    ret[group] = expand_weighted_list(data[group])

                return ret
            case {'type': 'flat_proportional', 'data': data}:
                return expand_weighted_list(data)
            case {'type': 'grouped', 'data': data}:
                return data
            case {'type': 'flat', 'data': data}:
                return data

    def __iter__(self):
        return list(self._data.keys())

    def __contains__(self, item):
        return item in self._data

    def random(self, key, group=None):
        match self._data[key]:
            case {'type': 'grouped_proportional', 'data': data} | \
                 {'type': 'grouped', 'data': data}:
                return rnd(data[group])
            case {'type': 'flat_proportional', 'data': data} | \
                 {'type': 'flat', 'data': data}:
                return rnd(data)


class Renderer:
    '''Encapsulates the state required for rendering items.'''
    def __init__(self, pool, dataset, logger=logger):
        self.env = jinja2.Environment(
            loader=jinja2.FunctionLoader(lambda x: None),
            autoescape=False,
            enable_async=True,
        )

        self._data = None
        self._pool = pool
        self._ready = asyncio.Event()
        self._ds = dataset

        self.logger = logger

    @staticmethod
    def _loader(name):
        with open(DATA_ROOT / f'{ name }.yaml') as f:
            return RenderData(yaml.load(f))

    async def load_data(self):
        '''Load required data.'''
        if not self._ready.is_set():
            loop = asyncio.get_running_loop()

            self.logger.info('Loading renderer data.')
            self._data = await loop.run_in_executor(self._pool, self._loader, self._ds.renderdata)
            self.logger.info('Finished loading renderer data.')

            self._ready.set()

        return True

    async def get_spell(self, item):
        '''Get a random spell for the given item.'''
        match await self._ds['spell'].random(**item['spell']):
            case (True, spell):
                return (True, spell)
            case (False, msg):
                return (False, msg)
            case False:
                return (False, 'Unable to get spell for item.')
            case ret:
                logging.warning(f'Searching random spell failed, got: { ret }')
                return (False, 'Unknown internal error.')

    async def render(self, item):
        '''Render an item.

           This recursively evaluates the item name as a jinja2 template,
           possibly with some extra formatting added.

           Returns either (True, x) where x is the rendered item, or
           (False, msg) where msg is an error message.'''
        match await self._render(item):
            case False:
                return (False, 'Unable to render item as renderer is not yet fully initilized.')
            case ret:
                return ret

    @check_ready
    async def _render(self, item):
        match item:
            case {'name': name, 'cls': _, 'caster_level': _}:
                t = '{{ item["name"] }} ({{ item["cls"].capitalize() }} CL {{ item["caster_level"] }})'
            case {'name': name, 'cost': _}:
                if '{{ spell }}' in name:
                    t = '{{ item["name"] }} ({{ item["cls"].capitalize() }} CL {{ item["caster_level"] }}, cost: {{ item["cost"] }} gp)'
                else:
                    t = '{{ item["name"] }} (cost: {{ item["cost"] }} gp)'
            case {'name': name}:
                if '{{ spell }}' in name:
                    t = '{{ item["name"] }} ({{ item["cls"].capitalize() }} CL {{ item["caster_level"] }})'
                else:
                    t = name
            case name if isinstance(name, str):
                item = {'name': item}
                if '{{ spell }}' in name:
                    t = '{{ item["name"] }} ({{ item["cls"].capitalize() }} CL {{ item["caster_level"] }})'
                else:
                    t = name
            case _:
                self.logger.error(f'Failed to render item: { item }.')
                return (False, 'Failed to render item.')

        n = ''
        i = 0

        while True:
            i += 1

            if i > MAX_TEMPLATE_RECURSION:
                self.logger.error('Too many levels of recursion in template: { template }.')
                return (False, 'Failed to render item.')

            if 'spell' in item:
                if 'rolled_spell' in item:
                    spell = item['rolled_spell']['name']
                    item['cls'] = item['rolled_spell']['cls']
                    item['caster_level'] = item['rolled_spell']['caster_level']
                else:
                    match await self.get_spell(item):
                        case (True, spell):
                            item['cls'] = spell['cls']
                            item['caster_level'] = spell['caster_level']
                            spell = spell['name']
                        case (False, msg):
                            return (False, msg)
            else:
                spell = None

            n = await self.env.from_string(t).render_async({'keys': self._data, 'spell': spell, 'item': item})

            if n == t:
                return (True, n)
            else:
                t = n
