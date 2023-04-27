# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

'''Constants for item data.'''

from pathlib import Path

DATA_ROOT = Path(__file__).parent / 'files'

RANK = [
    'minor',
    'medium',
    'major',
]

LIMITED_RANK = [
    'medium',
    'major',
]

SUBRANK = [
    'lesser',
    'greater',
]

SLOTLESS_SUBRANK = [
    'least',
    'lesser',
    'greater',
]
