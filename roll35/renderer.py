'''Render a message properly.'''

import asyncio
import logging

import jinja2

from .common import DATA_ROOT, expand_weighted_list, yaml, rnd

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
    def __init__(self, pool, bot, logger=logger):
        self.env = jinja2.Environment(
            loader=jinja2.FunctionLoader(lambda x: None),
            autoescape=False,
            enable_async=True,
        )

        self._data = None
        self._pool = pool
        self._ready = False
        self._bot = bot

        self.logger = logger

    @staticmethod
    def _loader():
        with open(DATA_ROOT / 'keys.yaml') as f:
            return RenderData(yaml.load(f))

    async def load_data(self):
        '''Load required data.'''
        if not self._ready:
            loop = asyncio.get_running_loop()

            self.logger.info('Loading renderer data.')
            self._data = await loop.run_in_executor(self._pool, self._loader)
            self.logger.info('Finished loading renderer data.')

            self._ready = True

        return True

    async def get_spell(self, item):
        '''Get a random spell for the given item.'''
        spell_agent = self._bot.get_cog('Spell').agent
        match await spell_agent.random(**item['spell']):
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
        if not self._ready:
            self.logger.warning('Asked to render item before data was loaded.')
            return (False, 'Unable to render item as renderer is not yet fully initilized.')

        match item:
            case {'name': name, 'cost': cost}:
                t = f'{ name } (cost: { cost } gp)'
            case {'name': name}:
                t = name
            case name if isinstance(name, str):
                t = name
            case _:
                self.logger.error('Failed to render item: { item }.')
                return (False, 'Failed to render item.')

        n = ''
        i = 0

        while True:
            i += 1

            if i > MAX_TEMPLATE_RECURSION:
                self.logger.error('Too many levels of recursion in template: { template }.')
                return (False, 'Failed to render item.')

            if 'spell' in item:
                match await self.get_spell(item):
                    case (True, spell):
                        spell = spell
                    case (False, msg):
                        return (False, msg)
            else:
                spell = None

            n = await self.env.from_string(t).render_async({'keys': self._data, 'spell': spell})

            if n == t:
                return (True, n)
            else:
                t = n
