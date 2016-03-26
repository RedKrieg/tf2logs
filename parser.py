#!/usr/bin/env python

import datetime
import re

class Line(object):
    """Represents a line in the log.  Base class"""
    patterns = {
        "user_re": '''"(?P<name>.*?)<(?P<server_id>\d+)>'''
                   '''<\[(?P<steam_id>[UIMGAPCgTcLa]:[0-4]:\d+)\]>'''
                   '''<(?P<team>\w+)>"''',
        "date_re": '''(?P<month>\d\d)/(?P<day>\d\d)/(?P<year>\d+)\s'''
                   '''-\s(?P<hour>\d\d):(?P<minute>\d\d):(?P<second>\d\d)''',
        "data_re": '''\((?P<name>\w+)\s"(?P<value>.*?)"\)'''
    }
    matcher = re.compile("$") # empty line for base class
    line_type = "unknown"

    def __init__(self, line):
        result = self.matcher.match(line)
        self.matched = result is not None
        if self.matched:
            self.result = self.parse(result)
        else:
            self.result = None

    def parse_timestamp(self, year, month, day, hour, minute, second, **kwargs):
        """Parses a timestamp from kwargs.
           Meant to be passed with **values"""
        self.timestamp = datetime.datetime(
            *( int(v) for v in (year, month, day, hour, minute, second) )
        )

    @classmethod
    def find_children(cls):
        # http://stackoverflow.com/a/3862957
        return cls.__subclasses__() + [g for s in cls.__subclasses__()
                                       for g in s.find_children()]

    @classmethod
    def identify(cls, line):
        """Returns an instance of a subclass of Line that matches line, or Line that does not match"""
        for subclass in cls.find_children():
            result = subclass(line)
            if result.matched:
                return result
        return cls(line)

    def parse(self, result):
        """Empty dictionary"""
        self.timestamp = None
        return result.groupdict()

class LogStartLine(Line):
    """Matches start of log"""
    matcher = re.compile(
        '''L\s{date_re}:\sLog file started(?P<data>(?:\s{data_re})+)'''.format(
            **Line.patterns
        )
    )
    line_type = "log_start"

    def parse(self, result):
        values = result.groupdict()
        data_dict = dict(re.findall(self.patterns["data_re"], values["data"]))
        self.parse_timestamp(**values)
        return data_dict

with open('match.log') as f:
    for line in f.readlines():
        result = Line.identify(line)
        if result.matched:
            print result.timestamp, result.result
