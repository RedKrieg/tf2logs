#!/usr/bin/env python3

from __future__ import print_function
import collections
import itertools
import json
import os
import parser
import timeseries

for filename in ['log_1288497.log']: #['l0321006.log']: #os.listdir('serverfiles/tf/logs'):
    world = parser.World()
    parsed = [ line for line in world.read_log_from_file(filename) ]
    for user in world.known_users.values():
        user.set_counter_durations(world.first_timestamp, world.last_timestamp)
        print("{}".format(user))
        for title, counter in user.counters.items():
            print("    {}".format(title))
            if isinstance(counter, timeseries.SparseTimeSeries):
                print("        {}".format(counter.sum()))
            else:
                for target, tscounter in counter.items():
                    print("        {:50}: {}".format(target, tscounter.sum()))
        damage = sum([item.sum() for item in [ damage for damage in user.counters["realdamage"].values() ]])
        duration = (world.last_timestamp - world.first_timestamp).total_seconds()
        print("    DPM")
        print("        {:.2f}".format(damage / duration * 60.0))
        print()
