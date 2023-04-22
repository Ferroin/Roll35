#!/usr/bin/env python3

import sys

version = sys.argv[1].split('.')
repo = sys.argv[2]

tags = []

tags.append(':'.join([repo, version[0]]))
tags.append(':'.join([repo, '.'.join(version[0:2])]))
tags.append(':'.join([repo, '.'.join(version[0:3])]))

print(','.join(tags))
