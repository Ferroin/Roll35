# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

'''Data handling for armor, shields, and weapons.'''

import logging

from . import agent
from . import types
from ..common import DATA_ROOT, yaml, make_weighted_entry, check_ready

logger = logging.getLogger(__name__)


def process_enchantment_table(items, basevalue):
    '''Process an armor or weapon enchantment table.'''
    ret = types.R35Map()

    for group in items:
        groupdata = dict()

        for value in items[group]:
            groupdata[value] = list(map(make_weighted_entry, items[group][value]))

        ret[group] = groupdata

    return ret


def get_enchant_bonus_costs(data, base):
    '''Compute the enchantment bonus costs for the specified ase item.'''
    if 'double' in base['tags']:
        masterwork = data['masterwork'] * 2
        enchant_base_cost = data['enchant_base_cost'] * 2
    else:
        masterwork = data['masterwork']
        enchant_base_cost = data['enchant_base_cost']

    return (
        masterwork,
        enchant_base_cost,
    )


def get_costs_and_bonus(enchants):
    '''Figure out the range of extra costs that a given list of enchantments might have.'''
    min_cost = -1
    max_cost = 0
    min_bonus = 0
    max_bonus = 0
    has_non_bonus = False

    for item in enchants:
        match item:
            case {'bonuscost': _, 'bonus': _}:
                raise ValueError(f'{ item } has both bonuscost and bonus keys.')
            case {'bonuscost': c}:
                if min_cost == -1:
                    min_cost = c
                else:
                    min_cost = min(min_cost, c)
                max_cost = max(max_cost, c)
                has_non_bonus = True
            case {'bonus': b}:
                min_cost = 0
                if min_bonus == 0:
                    min_bonus = b
                else:
                    min_bonus = min(min_bonus, b)
                max_bonus = max(max_bonus, b)
            case _:
                min_cost = 0
                has_non_bonus = True

    if has_non_bonus:
        min_bonus = 0

    return (min_cost, max_cost, min_bonus, max_bonus)


def get_costs(bonus, base, enchants, enchantments):
    if isinstance(list(enchantments.values())[0], dict):
        min_cost = float('inf')
        max_cost = 0

        for group in enchantments:
            c1, c2 = get_costs(bonus, base, enchants, enchantments[group])
            min_cost = min(min_cost, c1)
            max_cost = max(max_cost, c2)
    else:
        epossible = []

        for e in enchants:
            c1, c2, b1, b2 = get_costs_and_bonus(enchantments[e])
            epossible.append((
                c1,
                c2,
                max([b1, e]),
                max([b2, e]),
            ))

        min_cost = sum([
            sum(map(lambda x: x[0], epossible)),
            ((sum(map(lambda x: x[2], epossible)) + bonus) ** 2) * base,
        ])

        max_cost = sum([
            sum(map(lambda x: x[1], epossible)),
            ((sum(map(lambda x: x[3], epossible)) + bonus) ** 2) * base,
        ])

    return min_cost, max_cost


def create_xform(base, enchantments, specific):
    '''Produce a mapping function for adding costs to enchantment combos.'''
    def xform(x):
        match x:
            case {'specific': [group, rank, subrank]}:
                min_cost = specific[group][rank][subrank].costs.min
                max_cost = specific[group][rank][subrank].costs.max
            case {'specific': [rank, subrank]}:
                min_cost = specific[rank][subrank].costs.min
                max_cost = specific[rank][subrank].costs.max
            case {'bonus': bonus, 'enchants': []}:
                min_cost = (bonus ** 2) * base
                max_cost = (bonus ** 2) * base
            case {'bonus': bonus, 'enchants': [*enchants]}:
                min_cost, max_cost = get_costs(bonus, base, enchants, enchantments)
            case _:
                ValueError(f'{ x } is not a valid enchantment combination entry.')

        x['costrange'] = [
            min_cost,
            max_cost,
        ]

        return x

    return xform


class OrdnanceAgent(agent.Agent):
    def __init__(self, dataset, pool, name, logger=logger):
        super().__init__(dataset, pool, name, logger)

    @staticmethod
    def _loader(name):
        with open(DATA_ROOT / f'{ name }.yaml') as f:
            data = yaml.load(f)

        enchantments = process_enchantment_table(data['enchantments'], data['enchant_base_cost'])

        if types.RANK[1] in data['specific']:
            specific = agent.process_ranked_itemlist(data['specific'])
        else:
            specific = types.R35Map()

            for key in data['specific']:
                specific[key] = agent.process_ranked_itemlist(data['specific'][key])

        ret = agent.process_ranked_itemlist(
            data,
            create_xform(
                data['enchant_base_cost'],
                enchantments,
                specific,
            ),
        )

        ret['base'] = types.R35List(data['base'])
        ret['tags'] = agent.generate_tags_entry(data['base'])
        ret['enchantments'] = enchantments
        ret['specific'] = specific
        ret['masterwork'] = data['masterwork']
        ret['enchant_base_cost'] = data['enchant_base_cost']

        return ret

    async def random(self, rank, subrank, allow_specific=True, mincost=0, maxcost=float('inf')):
        return await super().random_pattern(rank, subrank, allow_specific, mincost, maxcost)

    @check_ready
    async def get_bonus_costs(self, base):
        return get_enchant_bonus_costs(self._data, base)
