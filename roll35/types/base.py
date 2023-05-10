# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

'''Data types used elsewhere in the types package.'''

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeVar

from .item import Item


@dataclass
class WeightedEntry:
    '''Data class for entries in weighted lists.'''
    weight: int
    value: Item | str


ItemEntry = TypeVar('ItemEntry', Item, WeightedEntry)
