'''Data handling for armor and shields.'''

import logging

from . import agent
from ..common import DATA_ROOT, yaml

logger = logging.getLogger(__name__)


class ArmorAgent(agent.Agent):
    def __init__(self, pool, logger=logger):
        self.name = 'armor'
        super().__init__(pool, logger)

    @staticmethod
    def _loader(_):
        with open(DATA_ROOT / 'armor.yaml') as f:
            data = yaml.load(f)

        ret = agent.process_ranked_itemlist(data)

        ret['base'] = list(data['base'])
        ret['tags'] = agent.generate_tags_entry(data['base'])
        ret['enchantments'] = agent.process_enchantment_table(data['enchantments'])

        ret['specific'] = dict()

        for key in data['specific']:
            ret['specific'][key] = agent.process_ranked_itemlist(data['specific'][key])

        return ret

    async def random(self, rank, subrank, allow_specific=True):
        return await super().random_pattern(rank, subrank, allow_specific)