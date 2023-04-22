#!/usr/bin/env python3
#
# Copyright (c) 2020 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

import csv

import yaml

data = list()

SAVE_KEYS = [
    'classes',
    'descriptor',
    'domains',
    'name',
    'school',
    'subschool',
]

print('Loading data...')

with open('./spells.csv', 'r') as csvfile:
    reader = csv.DictReader(csvfile)

    for line in reader:
        data.append(dict(line))

for item in data:
    print('Processing "' + item['name'] + '"...')
    item['classes'] = dict()
    item['domains'] = dict()

    if len(item['name'].split(', ')) > 1:
        name = item['name'].split(', ')
        name.reverse()
        item['name'] = ' '.join(name)

    for entry in item['spell_level'].split(', '):
        entry = entry.split()
        cls = entry[0] if len(entry) == 2 else entry[1]
        lvl = int(entry[-1])

        if cls == 'sorcerer/wizard':
            cls = 'wizard'
        elif cls == 'cleric/oracle':
            cls = 'cleric'

        item['classes'][cls] = lvl

    for entry in item['domain'].split(', '):
        if entry:
            entry = entry.split()
            domain = '_'.join(entry[:-1]).lower()
            lvl = int(entry[-1].strip('()'))

            item['domains'][domain] = lvl

    item['descriptor'] = item['descriptor'].replace('-', '_')

    for key in list(item.keys()):
        if key not in SAVE_KEYS:
            del item[key]

print('Sorting data...')
data.sort(key=lambda i: i['name'])

print('Writing data...')

with open('./spells.yaml', 'w') as yamlfile:
    yamlfile.write(yaml.dump(data, width=120, indent=2))
