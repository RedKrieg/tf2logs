#!/usr/bin/env python3

from __future__ import print_function
import collections
import itertools
import json
import os
import parser
import timeseries

for filename in ['l0321006.log']:#['log_1288497.log']: #['l0321006.log']: #os.listdir('serverfiles/tf/logs'):
    world = parser.World()
    parsed = [ line for line in world.read_log_from_file(filename) ]
    for user in world.known_users.values():
        user.set_counter_durations(world.first_timestamp, world.last_timestamp)
        print("{}".format(user))
        for title, counter in user.counters.items():
            print("    {}".format(title))
            for target, tscounter in counter.items():
                print("        {:50}: {}".format(target, tscounter.sum()))
        damage = sum(user.counters["realdamage"].totals.values())
        duration = (world.last_timestamp - world.first_timestamp).total_seconds()
        print("    DPM")
        print("        {:.2f}".format(damage / duration * 60.0))
        print()

for user in world.known_users.values():
    with open('data.json', 'w') as f:
        json.dump([
            {
                "key": "{}: {}".format(user, stat),
                "values": [
                    ( timestamp.timestamp() * 1000, value )
                    for timestamp, value in user.counters[stat].totals.items()
                ]
            } for stat in ("realdamage", "damage_received")
        ], f, sort_keys=True, indent=4)
