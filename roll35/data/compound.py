'''Data handling for compound item lists.'''

import logging

from . import agent
from ..common import DATA_ROOT, yaml

logger = logging.getLogger(__name__)


class CompoundAgent(agent.Agent):
    def __init__(self, pool, name, logger=logger):
        self.name = name
        super().__init__(pool, logger)

    @staticmethod
    def _loader(name):
        with open(DATA_ROOT / f'{ name }.yaml') as f:
            data = yaml.load(f)

        ret = agent.process_compound_itemlist(data)

        return ret

    async def random(self, rank=None):
        return await super().random_compound(rank)
