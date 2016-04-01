#!/usr/bin/env python3

from __future__ import print_function
import collections
import itertools
import json
import math
import os
import parser

for filename in ['log_1288497.log']: #['l0321006.log']: #os.listdir('serverfiles/tf/logs'):
    world = parser.World()
    tsdata = []
    for ts, group in itertools.groupby(
        world.read_log_from_file(filename),
        key=lambda line: math.floor(
            line.timestamp.timestamp() / 6
        ) * 6 if isinstance(line, parser.TimeLine) else 0
    ):
        for line in group:
            if isinstance(line, parser.TournamentModeLine):
                tsdata = []
        tsdata.append({
           user.team_class(): {
               title: counter if isinstance(counter, int) else {
                   target.team_class() if isinstance(target, parser.User) else target: count
                   for target, count in counter.items()
               }
               for title, counter in user.counters.items()
           } for user in world.known_users.values()
        })
    for user in world.known_users.values():
        print("{}".format(user))
        for title, counter in user.counters.items():
            if hasattr(counter, 'items') and len(counter) > 0:
                print("    {}".format(title))
                for target, count in counter.items():
                    print("        {:50}: {}".format(
                        target,
                        count
                    ))
            elif not hasattr(counter, 'items'):
                print("    {}".format(title))
                print("        {}".format(counter))
        damage = sum([ damage for target, damage in user.counters["realdamage"].items() ])
        duration = (world.last_timestamp - world.first_timestamp).total_seconds()
        print("    DPM")
        print("        {:.2f}".format(damage / duration * 60.0))
        print()
    print(json.dumps(tsdata, indent=4))
