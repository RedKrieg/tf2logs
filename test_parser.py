#!/usr/bin/env python

import os
import parser

for filename in os.listdir('serverfiles/tf/logs'):
    with open('serverfiles/tf/logs/{}'.format(filename)) as f:
        for line in f.readlines():
            result = parser.Line.identify(line)
            if result.matched:
                if '(' in line and not isinstance(result, parser.DataLine) and not isinstance(result, parser.SayLine):
                    print repr(result)
            else:
                print line.strip()
