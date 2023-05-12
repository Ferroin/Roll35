# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

'''Data classes defining item formats.'''

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, KW_ONLY, field
from typing import Union, Literal, TypedDict

from .ranks import RankWeights

EnchantBonus = int
Cost = int | float
_Cost = Cost | Literal['varies']
CostRange = tuple[Cost, Cost]
Tag = str


@dataclass
class BaseItem:
    '''Base class for item entries.'''
    _: KW_ONLY
    weight: int | None = None
    reroll: Sequence[str] | None = None
    cost: _Cost | None = None
    costrange: CostRange | None = None
    costmult: Cost | None = None


class SpellParams(TypedDict, total=False):
    '''Parameters for rolling a spell for an item.'''
    level: int
    cls: str


@dataclass
class SpellEntry:
    '''Data class representing a specific spell.'''
    name: str
    level: int
    cls: str
    caster_level: int
    tags: set[str] = field(default_factory=set)


@dataclass
class SpellItem(BaseItem):
    '''Base class for an item with an embedded spell.'''
    _: KW_ONLY
    spell: SpellParams
    rolled_spell: SpellEntry | None = None
    cls: str | None = None
    level: int | None = None
    caster_level: int | None = None


@dataclass
class SimpleItem(BaseItem):
    '''A basic item entry.'''
    _: KW_ONLY
    name: str = ''
    reroll: Sequence[str] | None = None


@dataclass
class SimpleSpellItem(SimpleItem, SpellItem):
    '''A basic item entry with an embedded spell.'''
    pass


@dataclass
class OrdnancePattern(BaseItem):
    '''A pattern entry for constructing an ordnance item.'''
    bonus: EnchantBonus | None = None
    enchants: list[EnchantBonus] | None = None
    specific: list[str] | None = None


OrdnanceSpecific = SimpleItem


@dataclass
class OrdnanceBaseItem(BaseItem):
    '''A base ordnance item entry.'''
    type: str
    tags: set[Tag]
    name: str
    count: int | None = None


EnchantLimits = TypedDict('EnchantLimits', {'only': Union[list[Tag]], 'not': Union[list[Tag]]}, total=False)


@dataclass
class OrdnanceEnchant(BaseItem):
    '''An enchantment entry for ordnance items.'''
    name: str
    bonuscost: Cost | None = None
    bonus: EnchantBonus | None = None
    exclude: list[str] | None = None
    remove: list[str] | None = None
    add: list[str] | None = None
    limit: EnchantLimits | None = None


OrdnanceItem = Union[OrdnancePattern, OrdnanceSpecific, OrdnanceBaseItem, OrdnanceEnchant]


@dataclass
class CompoundItem(SimpleItem, RankWeights):
    '''An entry for an item in a compound item list.'''
    pass


@dataclass
class CompoundSpellItem(CompoundItem, SpellItem):
    '''An entry for a compound item with an embedded spell.'''
    pass


Item = BaseItem | SimpleItem | SimpleSpellItem | OrdnanceItem | CompoundItem | CompoundSpellItem
