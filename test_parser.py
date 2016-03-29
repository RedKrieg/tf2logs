#!/usr/bin/env python3

from __future__ import print_function
import os
import parser

for filename in ['log_1288497.log']: #['l0321006.log']: #os.listdir('serverfiles/tf/logs'):
    world = parser.World()
    with open('serverfiles/tf/logs/{}'.format(filename)) as f:
        for line in f.readlines():
            result = parser.Line.identify(world, line)
            if result.matched:
                pass
                #print repr(result)
            else:
                pass # we have to log lines we can't parse for production
                #print line.strip()
    for user in world.known_users.values():
        print("{}".format(user))
        for title, counter in user.counters.items():
            print("    {}".format(title))
            if hasattr(counter, 'items'):
                for target, count in counter.items():
                    print("        {:50}: {}".format(
                        target,
                        count
                    ))
            else:
                print("        {}".format(counter))
        damage = sum([ damage for target, damage in user.counters["realdamage"].items() ])
        duration = (world.last_timestamp - world.first_timestamp).total_seconds()
        print("    DPM")
        print("        {:.2f}".format(damage / duration * 60.0))
