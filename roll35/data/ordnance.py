# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

'''Data handling for armor, shields, and weapons.'''

import logging
import random

from . import agent
from . import constants
from .. import types
from ..common import make_weighted_entry, check_ready, norm_string, did_you_mean, bad_return
from ..retcode import Ret

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
    '''Determine the range of possible costs for a set of enchantments.'''
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


def generate_tags_entry(items):
    '''Generate a list of tags based on a list of items.'''
    tags = map(lambda x: set(x['tags']), items)
    tags = set.union(*tags)
    return tags | {x['type'] for x in items}


class OrdnanceAgent(agent.Agent):
    '''Data agent for weapon or armor item data.'''
    @staticmethod
    def _process_data(data):
        enchantments = process_enchantment_table(data['enchantments'], data['enchant_base_cost'])

        if constants.RANK[1] in data['specific']:
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
        ret['tags'] = generate_tags_entry(data['base'])
        ret['enchantments'] = enchantments
        ret['specific'] = specific
        ret['masterwork'] = data['masterwork']
        ret['enchant_base_cost'] = data['enchant_base_cost']

        return ret

    async def random(self, **kwargs):
        return await self.random_pattern(**kwargs)

    @check_ready
    @agent.ensure_costs
    async def random_pattern(self, rank, subrank, allow_specific=True, mincost=None, maxcost=None):
        '''Return a random item pattern to use to generate a random item from.'''
        match rank:
            case None:
                rank = random.choice(constants.RANK)
            case rank if self._valid_rank(rank):
                pass
            case _:
                raise ValueError(f'Invalid rank for { self.name }: { rank }')

        if subrank is None:
            subrank = random.choice(constants.SUBRANK)

        items = agent.costfilter(self._data[rank][subrank], mincost, maxcost)

        if allow_specific:
            if items:
                return random.choice(items)['value']
            else:
                return Ret.NO_MATCH
        else:
            match list(filter(lambda x: 'specific' not in x['value'], items)):
                case []:
                    return Ret.NO_MATCH
                case [*items]:
                    return random.choice(items)['value']

    @check_ready
    async def get_base(self, pool, name):
        '''Get a base item by name.

           On a mismatch, returns a list of possible names that might
           have been intended.'''
        items = self._data['base']
        norm_name = norm_string(name)

        match next((x for x in items if norm_string(x['name']) == norm_name), None):
            case None:
                match await self._process_async(
                    pool,
                    did_you_mean,
                    [items, norm_name],
                ):
                    case (Ret.OK, msg):
                        return (
                            Ret.FAILED,
                            f'{ name } is not a recognized item.\n { msg }'
                        )
                    case (ret, msg) if ret is not Ret.OK:
                        return (ret, msg)
                    case ret:
                        logger.error(bad_return(ret))
                        return (Ret.FAILED, 'Unknown internal error.')
            case item:
                return (Ret.OK, item)

    @check_ready
    async def random_base(self, tags=[]):
        '''Get a base item at random.'''
        items = self._data['base']

        match tags:
            case []:
                pass
            case [*tags]:
                items = list(filter(
                    lambda x: all(
                        map(
                            lambda y: y == x['type'] or y in x['tags'],
                            tags
                        )
                    ), items
                ))
            case _:
                raise ValueError('Tags must be a list.')

        if items:
            return random.choice(items)
        else:
            return Ret.NO_MATCH

    @check_ready
    async def random_enchant(self, group, bonus, enchants=[], tags=[]):
        '''Roll a random enchantment.'''
        items = self._data['enchantments'][group][bonus]

        def _efilter(x):
            result = True

            match x:
                case {'exclude': excluded}:
                    result = result and not any(lambda y: y in excluded, enchants)

            match x:
                case {'limit': {'only': limit}}:
                    result = result and any(lambda y: y in limit, tags)
                case {'limit': {'not': limit}}:
                    result = result and not any(lambda y: y in limit, tags)

            return result

        match list(filter(_efilter, items)):
            case []:
                return Ret.NO_MATCH
            case [*opts]:
                return random.choice(opts)['value']

    @check_ready
    @agent.ensure_costs
    async def random_specific(self, *args, mincost=None, maxcost=None):
        '''Roll a random specific item.'''
        match args:
            case [_, _, _]:
                group = args[0]
                rank = args[1]
                subrank = args[2]
            case [_, _]:
                group = False
                rank = args[0]
                subrank = args[1]
            case _:
                raise ValueError(f'Invalid arguments for { self.name }.random_specific: { args }')

        match rank:
            case None:
                rank = random.choice(constants.RANK)
            case rank if self._valid_rank(rank):
                pass
            case _:
                raise ValueError(f'Invalid rank for { self.name }: { rank }')

        if subrank is None:
            subrank = random.choice(constants.SUBRANK)

        items = self._data['specific']

        if group:
            if group not in items:
                raise ValueError(f'Unrecognized item type for { self.name }: { rank }')

            items = items[group]

        items = agent.costfilter(items[rank][subrank], mincost, maxcost)

        if items:
            return random.choice(items)['value']
        else:
            return Ret.NO_MATCH

    @check_ready
    async def get_bonus_costs(self, base):
        '''Get the bonus costs associated with the given item.'''
        return get_enchant_bonus_costs(self._data, base)

    @check_ready
    async def tags(self):
        '''Get a list of recognized tags.'''
        if 'tags' in self._data:
            return list(self._data['tags'])
        else:
            return Ret.NO_MATCH
