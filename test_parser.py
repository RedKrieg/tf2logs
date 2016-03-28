#!/usr/bin/env python

import os
import parser

for filename in os.listdir('serverfiles/tf/logs'):
    with open('serverfiles/tf/logs/{}'.format(filename)) as f:
        for line in f.readlines():
            result = parser.Line.identify(line)
            if result.matched:
                if isinstance(result, parser.DataLine):
                    for k, v in result.data.iteritems():
                        if type(v) is str:
                            print "{:20}: {!r}".format(k, v)
            else:
                pass
                #print line.strip()

