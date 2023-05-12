# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

'''Data types used elsewhere in the types package.'''

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeVar, Generic

from .item import Item

T = TypeVar('T')


@dataclass
class WeightedEntry(Generic[T]):
    '''Data class for entries in weighted lists.'''
    weight: int
    value: T


ItemEntry = TypeVar('ItemEntry', Item, WeightedEntry[Item])
