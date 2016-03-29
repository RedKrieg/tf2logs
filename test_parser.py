#!/usr/bin/env python

import os
import parser

for filename in ['l0321006.log']: #os.listdir('serverfiles/tf/logs'):
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
        print user.name
        for title, counter in user.counters.iteritems():
            print "    {}".format(title)
            if hasattr(counter, 'iteritems'):
                for target, count in counter.iteritems():
                    print "        {:50}: {}".format(
                        target,
                        count
                    )
            else:
                print "        {}".format(counter)
