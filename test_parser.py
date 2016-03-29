#!/usr/bin/env python

import os
import parser

for filename in os.listdir('serverfiles/tf/logs'):
    world = parser.World()
    with open('serverfiles/tf/logs/{}'.format(filename)) as f:
        for line in f.readlines():
            result = parser.Line.identify(world, line)
            if result.matched:
                if isinstance(result, parser.DataLine):
                    for k, v in result.data.iteritems():
                        if type(v) is str:
                            pass #print "{:20}: {!r}".format(k, v)
                print repr(result)
            else:
                pass
                #print line.strip()
    for user in world.known_users.values():
        print repr(user)
