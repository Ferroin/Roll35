# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

'''Data handling for compound item lists.'''

import logging

from . import agent
from ..common import DATA_ROOT, yaml

logger = logging.getLogger(__name__)


def create_spellmult_xform(classes):
    def xform(x):
        levels = map(lambda x: x['levels'], classes.values())

        match x:
            case {'spell': {'level': level, 'class': 'minimum'}, 'costmult': costmult}:
                levels = filter(lambda x: len(x) > level and x[level] is not None, levels)
                levels = set(map(lambda x: x[level], levels))
                minlevel = min(levels)
                x['cost'] = minlevel * costmult
            case {'spell': {'level': level}, 'costmult': costmult}:
                levels = filter(lambda x: len(x) > level and x[level] is not None, levels)
                levels = set(map(lambda x: x[level], levels))
                minlevel = min(levels)
                maxlevel = max(levels)
                x['costrange'] = [
                    minlevel * costmult,
                    maxlevel * costmult,
                ]
            case _:
                raise ValueError(f'Invalid compound spell entry { x }')

        return x

    return xform


class CompoundAgent(agent.Agent):
    def __init__(self, dataset, pool, name, logger=logger):
        super().__init__(dataset, pool, name, logger)

    @staticmethod
    def _loader(name):
        with open(DATA_ROOT / f'{ name }.yaml') as f:
            data = yaml.load(f)

        ret = agent.process_compound_itemlist(data)

        return ret

    async def random(self, **kwargs):
        return await super().random_compound(**kwargs)


class CompoundSpellAgent(CompoundAgent):
    @staticmethod
    def _loader(name, classes):
        with open(DATA_ROOT / f'{ name }.yaml') as f:
            data = yaml.load(f)

        ret = agent.process_compound_itemlist(
            data,
            create_spellmult_xform(classes)
        )

        return ret

    async def load_data(self):
        '''Load data for this agent.'''
        if not self._ready.is_set():
            self.logger.info('Fetching class data.')

            classes = await self._ds['classes'].W_classdata()

            self.logger.info(f'Loading { self.name } data.')
            self._data = await self._process_async(self._loader, [self.name, classes])
            self.logger.info(f'Finished loading { self.name } data.')

            self._ready.set()

        return True

    async def random(self, cls=None, **kwargs):
        match await super().random_compound(**kwargs):
            case None:
                return (False, 'No items match specified cost range.')
            case {'spell': spell, **item}:
                match await self._ds['spell'].random(**spell):
                    case False:
                        return (False, 'Failed to roll random spell for item: spell data not ready.')
                    case (False, msg):
                        return (False, f'Failed to roll random spell for item: { msg }')
                    case (True, spell):
                        if 'costmult' in item:
                            item['cost'] = item['costmult'] * spell['caster_level']

                        item['rolled_spell'] = spell
                        item['spell'] = spell
                        return (True, item)
                    case ret:
                        self.logger.warning(f'Searching random spell failed, got: { ret }')
                        return (False, 'Unknown internal error.')
            case item:
                return (True, item)
