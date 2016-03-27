#!/usr/bin/env python

import datetime
import re

patterns = {
    "user_re": '''"(?P<username>.*?)<(?P<server_id>\d+)>'''
               '''<(?P<steam_id>\[(?:[UIMGAPCgTcLa]:[0-4]:\d+)\]|(?:BOT))>'''
               '''<(?P<team>\w*)>"''',
    "date_re": '''(?P<month>\d\d)/(?P<day>\d\d)/(?P<year>\d+)\s'''
               '''-\s(?P<hour>\d\d):(?P<minute>\d\d):(?P<second>\d\d)''',
    "data_re": '''\((?P<name>\w+)\s"(?P<value>.*?)"\)''',
}

class User(object):
    """Represents a User"""
    def __init__(self, user_text):
        """<user_text> is anything that will match user_re successfully"""
        match = re.match(patterns["user_re"], user_text)
        user_data = match.groupdict()
        self.name = user_data["username"]
        self.steam_id = user_data["steam_id"]
        self.team = user_data["team"]
        self.text = user_text

    def __str__(self):
        return "{steam_id} {name} ({team})".format(**self.__dict__)

class Line(object):
    """Represents a line in the log.  Base class"""
    matcher = re.compile("$") # empty line for base class

    def __init__(self, line):
        result = self.matcher.match(line)
        self.line = line
        self.matched = result is not None
        if self.matched:
            self.parse(result)

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
        self.data = result.groupdict()

    def parse_values(self, values_string):
        return dict(re.findall(patterns["data_re"], values_string))

class LogStartLine(Line):
    """Matches start of log"""
    matcher = re.compile(
        '''L\s{date_re}:\sLog file started(?P<data>(?:\s{data_re})*)'''.format(
            **patterns
        )
    )

    def parse(self, result):
        values = result.groupdict()
        self.parse_timestamp(**values)
        self.data = self.parse_values(values["data"])

def LogEndLine(Line):
    """Matches end of log"""
    matcher = re.compile(
        '''L\s{date_re}:\sLog file closed.'''
    )

    def parse(self, result):
        values = result.groupdict()
        self.parse_timestamp(**values)

class TournamentModeLine(Line):
    """Matches the beginning of tournament mode"""
    matcher = re.compile(
        '''L\s{date_re}:\s Tournament mode started'''
    )

    def parse(self, result):
        values = result.groupdict()
        self.parse_timestamp(**values)

class TeamNameLine(Line):
    """Matches team name in tournament mode"""
    matcher = re.compile('''(?P<team>Red|Blue) Team: (?P<name>.*)''')

    def parse(self, result):
        values = result.groupdict()
        self.timestamp = None
        self.team = values["team"]
        self.name = values["name"]

class SayLine(Line):
    """Matches say lines"""
    matcher = re.compile(
        '''L\s{date_re}:\s(?P<source_user>{user_re})\ssay\s"(?P<text>.*)"$'''.format(
            **patterns
        )
    )

    def parse(self, result):
        values = result.groupdict()
        self.parse_timestamp(**values)
        self.text = values["text"]
        self.source = User(values["source_user"])

class SayTeamLine(SayLine):
    """Matches say_team lines"""
    matcher = re.compile(
        '''L\s{date_re}:\s(?P<source_user>{user_re})\ssay_team\s"(?P<text>.*)"$'''.format(
            **patterns
        )
    )

    def parse(self, result):
        super(self.__class__, self).parse(result)
        self.team = self.source.team

class DamagePlayerTriggerLine(Line):
    """Matches when damage is triggered on a player"""
    matcher = re.compile((
        '''L\s{date_re}:\s(?P<source_user>".*?")\striggered "damage" '''
        '''against (?P<target_user>".*?")(?P<data>(?:\s{data_re})*)'''
    ).format(**patterns))

    def parse(self, result):
        values = result.groupdict()
        self.parse_timestamp(**values)
        self.source = User(values["source_user"])
        self.target = User(values["target_user"])
        self.data = self.parse_values(values["data"])

class KillLine(Line):
    """Matches when a player kills another player"""
    matcher = re.compile((
        '''L\s{date_re}:\s(?P<source_user>".*?")\skilled\s'''
        '''(?P<target_user>".*?")\swith\s"(?P<weapon>.*?)"'''
        '''(?P<data>(?:\s{data_re})*)'''
    ).format(**patterns))

    def parse(self, result):
        values = result.groupdict()
        self.parse_timestamp(**values)
        self.source = User(values["source_user"])
        self.target = User(values["target_user"])
        self.weapon = values["weapon"]
        self.data = self.parse_values(values["data"])

class KillAssistLine(Line):
    """Matches when a player gets a kill assist"""
    matcher = re.compile((
        '''L\s{date_re}:\s(?P<source_user>".*?")\striggered "kill assist"'''
        ''' against (?P<target_user>".*?")(?P<data>(?:\s{data_re})*)'''
    ).format(**patterns))

    def parse(self, result):
        values = result.groupdict()
        self.parse_timestamp(**values)
        self.source = User(values["source_user"])
        self.target = User(values["target_user"])
        self.data = self.parse_values(values["data"])

class SuicideLine(Line):
    """Matches when a player suicides"""
    matcher = re.compile((
        '''L\s{date_re}:\s(?P<source_user>".*?")\scommitted suicide with '''
        '''"(?P<weapon>.*?)"(?P<data>(?:\s{data_re})*)'''
    ).format(**patterns))

    def parse(self, result):
        values = result.groupdict()
        self.parse_timestamp(**values)
        self.source = User(values["source_user"])
        self.weapon = values["weapon"]
        self.data = self.parse_values(values["data"])

class WorldTriggerLine(Line):
    """Matches world triggers"""
    matcher = re.compile((
        '''L\s{date_re}:\sWorld triggered "(?P<event>.*?)"'''
        '''(?P<data>(?:\s{data_re})*)'''
    ).format(**patterns))

    def parse(self, result):
        values = result.groupdict()
        self.parse_timestamp(**values)
        self.event = values["event"]
        self.data = self.parse_values(values["data"])

class TeamStatusLine(Line):
    """Matches team status lines"""
    matcher = re.compile((
        '''L\s{date_re}:\sTeam "(?P<team>.*?)" current score "(?P<score>\d+)'''
        '''" with "(?P<player_count>\d+)" players'''
    ).format(**patterns))

    def parse(self, result):
        values = result.groupdict()
        self.parse_timestamp(**values)
        self.team = values["team"]
        self.score = values["score"]
        self.player_count = values["player_count"]

class CapturePointLine(Line):
    """Matches team capture lines"""
    matcher = re.compile((
        '''L\s{date_re}:\sTeam "(?P<team>.*?)" triggered "pointcaptured"'''
        '''(?P<data>(?:\s{data_re})*)'''
    ).format(**patterns))

    def parse(self, result):
        values = result.groupdict()
        self.parse_timestamp(**values)
        self.team = values["team"]
        self.data = self.parse_values(values["data"])

class ItemPickUpLine(Line):
    """Matches item pickups"""
    matcher = re.compile((
        '''L\s{date_re}:\s(?P<source_user>".*?")\spicked up item "'''
        '''(?P<item>.*?)"(?P<data>(?:\s{data_re})*)'''
    ).format(**patterns))

    def parse(self, result):
        values = result.groupdict()
        self.parse_timestamp(**values)
        self.source = User(values["source_user"])
        self.item = values["item"]
        self.data = self.parse_values(values["data"])

class HealTriggerLine(Line):
    """Matches healing lines"""
    matcher = re.compile((
        '''L\s{date_re}:\s(?P<source_user>".*?")\striggered "healed" '''
        '''against (?P<target_user>".*?")(?P<data>(?:\s{data_re})*)'''
    ).format(**patterns))

    def parse(self, result):
        values = result.groupdict()
        self.parse_timestamp(**values)
        self.source = User(values["source_user"])
        self.target = User(values["target_user"])
        self.data = self.parse_values(values["data"])

class ChargeReadyTriggerLine(Line):
    """Matches uber deploy lines"""
    matcher = re.compile((
        '''L\s{date_re}:\s(?P<source_user>".*?")\striggered '''
        '''"chargeready"(?P<data>(?:\s{data_re})*)'''
    ).format(**patterns))

    def parse(self, result):
        values = result.groupdict()
        self.parse_timestamp(**values)
        self.source = User(values["source_user"])
        self.data = self.parse_values(values["data"])

class ChargeDeployTriggerLine(Line):
    """Matches uber deploy lines"""
    matcher = re.compile((
        '''L\s{date_re}:\s(?P<source_user>".*?")\striggered '''
        '''"chargedeployed"(?P<data>(?:\s{data_re})*)'''
    ).format(**patterns))

    def parse(self, result):
        values = result.groupdict()
        self.parse_timestamp(**values)
        self.source = User(values["source_user"])
        self.data = self.parse_values(values["data"])

class ChargeEndedTriggerLine(Line):
    """Matches uber deploy lines"""
    matcher = re.compile((
        '''L\s{date_re}:\s(?P<source_user>".*?")\striggered '''
        '''"chargeended"(?P<data>(?:\s{data_re})*)'''
    ).format(**patterns))

    def parse(self, result):
        values = result.groupdict()
        self.parse_timestamp(**values)
        self.source = User(values["source_user"])
        self.data = self.parse_values(values["data"])

class UberEmptyTriggerLine(Line):
    """Matches uber empty lines"""
    matcher = re.compile((
        '''L\s{date_re}:\s(?P<source_user>".*?")\striggered '''
        '''"empty_uber"(?P<data>(?:\s{data_re})*)'''
    ).format(**patterns))

    def parse(self, result):
        values = result.groupdict()
        self.parse_timestamp(**values)
        self.source = User(values["source_user"])
        self.data = self.parse_values(values["data"])

class UberAdvantageLostTriggerLine(Line):
    """Matches when uber advantage is lost"""
    matcher = re.compile((
        '''L\s{date_re}:\s(?P<source_user>".*?")\striggered '''
        '''"lost_uber_advantage"(?P<data>(?:\s{data_re})*)'''
    ).format(**patterns))

    def parse(self, result):
        values = result.groupdict()
        self.parse_timestamp(**values)
        self.source = User(values["source_user"])
        self.data = self.parse_values(values["data"])

class MedicDeathTrigger(Line):
    """Matches when medic deaths are recorded"""
    matcher = re.compile((
        '''L\s{date_re}:\s(?P<source_user>".*?")\striggered '''
        '''"medic_death" against (?P<target_user>".*?")(?P<data>(?:\s{data_re})*)'''
    ).format(**patterns))

    def parse(self, result):
        values = result.groupdict()
        self.parse_timestamp(**values)
        self.source = User(values["source_user"])
        self.target = User(values["target_user"])
        self.data = self.parse_values(values["data"])

class MedicDeathExTrigger(Line):
    """Matches when medic deaths are recorded again?"""
    matcher = re.compile((
        '''L\s{date_re}:\s(?P<source_user>".*?")\striggered '''
        '''"medic_death_ex"(?P<data>(?:\s{data_re})*)'''
    ).format(**patterns))

    def parse(self, result):
        values = result.groupdict()
        self.parse_timestamp(**values)
        self.source = User(values["source_user"])
        self.data = self.parse_values(values["data"])

class FirstHealAfterSpawnTrigger(Line):
    """Matches when medic heals after spawning"""
    matcher = re.compile((
        '''L\s{date_re}:\s(?P<source_user>".*?")\striggered '''
        '''"first_heal_after_spawn"(?P<data>(?:\s{data_re})*)'''
    ).format(**patterns))

    def parse(self, result):
        values = result.groupdict()
        self.parse_timestamp(**values)
        self.source = User(values["source_user"])
        self.data = self.parse_values(values["data"])

class PlayerExtinguishedTriggerLine(Line):
    """Matches extinguish lines"""
    matcher = re.compile((
        '''L\s{date_re}:\s(?P<source_user>".*?")\striggered '''
        '''"player_extinguished" against (?P<target_user>".*?")'''
        ''' with "(?P<weapon>.*?)"(?P<data>(?:\s{data_re})*)'''
    ).format(**patterns))

    def parse(self, result):
        values = result.groupdict()
        self.parse_timestamp(**values)
        self.source = User(values["source_user"])
        self.target = User(values["target_user"])
        self.weapon = values["weapon"]
        self.data = self.parse_values(values["data"])

class KillObjectLine(Line):
    """Matches 'killedobject' lines"""
    matcher = re.compile((
        '''L\s{date_re}:\s(?P<source_user>".*?")\striggered '''
        '''"killedobject"(?P<data>(?:\s{data_re})*)'''
    ).format(**patterns))

    def parse(self, result):
        values = result.groupdict()
        self.parse_timestamp(**values)
        self.source = User(values["source_user"])
        self.data = self.parse_values(values["data"])

class SpawnLine(Line):
    """Matches 'spawned' lines"""
    matcher = re.compile((
        '''L\s{date_re}:\s(?P<source_user>".*?")\sspawned as "'''
        '''(?P<class>.*?)"'''
    ).format(**patterns))

    def parse(self, result):
        values = result.groupdict()
        self.parse_timestamp(**values)
        self.source = User(values["source_user"])
        self.source.player_class = values["class"]

class PlayerBuiltObjectTriggerLine(Line):
    """Matches building lines"""
    matcher = re.compile((
        '''L\s{date_re}:\s(?P<source_user>".*?")\striggered '''
        '''"player_builtobject"(?P<data>(?:\s{data_re})*)'''
    ).format(**patterns))

    def parse(self, result):
        values = result.groupdict()
        self.parse_timestamp(**values)
        self.source = User(values["source_user"])
        self.data = self.parse_values(values["data"])

class PlayerCarryObjectTriggerLine(Line):
    """Matches player carrying objects"""
    matcher = re.compile((
        '''L\s{date_re}:\s(?P<source_user>".*?")\striggered '''
        '''"player_carryobject"(?P<data>(?:\s{data_re})*)'''
    ).format(**patterns))

    def parse(self, result):
        values = result.groupdict()
        self.parse_timestamp(**values)
        self.source = User(values["source_user"])
        self.data = self.parse_values(values["data"])

class PlayerDropObjectTriggerLine(Line):
    """Matches a player dropping an object"""
    matcher = re.compile((
        '''L\s{date_re}:\s(?P<source_user>".*?")\striggered '''
        '''"player_dropobject"(?P<data>(?:\s{data_re})*)'''
    ).format(**patterns))

    def parse(self, result):
        values = result.groupdict()
        self.parse_timestamp(**values)
        self.source = User(values["source_user"])
        self.data = self.parse_values(values["data"])

class ObjectDetonatedTriggerLine(Line):
    """Matches a player detonating an object"""
    matcher = re.compile((
        '''L\s{date_re}:\s(?P<source_user>".*?")\striggered '''
        '''"object_detonated"(?P<data>(?:\s{data_re})*)'''
    ).format(**patterns))

    def parse(self, result):
        values = result.groupdict()
        self.parse_timestamp(**values)
        self.source = User(values["source_user"])
        self.data = self.parse_values(values["data"])

class DominationTriggerLine(Line):
    """Matches domination lines"""
    matcher = re.compile((
        '''L\s{date_re}:\s(?P<source_user>".*?")\striggered '''
        '''"domination" against (?P<target_user>".*?")'''
    ).format(**patterns))

    def parse(self, result):
        values = result.groupdict()
        self.parse_timestamp(**values)
        self.source = User(values["source_user"])
        self.target = User(values["target_user"])

class RevengeTriggerLine(Line):
    """Matches revenge lines"""
    matcher = re.compile((
        '''L\s{date_re}:\s(?P<source_user>".*?")\striggered '''
        '''"revenge" against (?P<target_user>".*?")'''
    ).format(**patterns))

    def parse(self, result):
        values = result.groupdict()
        self.parse_timestamp(**values)
        self.source = User(values["source_user"])
        self.target = User(values["target_user"])

class CaptureBlockedTriggerLine(Line):
    """Matches capture point blocked lines"""
    matcher = re.compile((
        '''L\s{date_re}:\s(?P<source_user>".*?")\striggered '''
        '''"captureblocked"(?P<data>(?:\s{data_re})*)'''
    ).format(**patterns))

    def parse(self, result):
        values = result.groupdict()
        self.parse_timestamp(**values)
        self.source = User(values["source_user"])
        self.data = self.parse_values(values["data"])

class PlayerDisconnectedLine(Line):
    """Matches player disconnect lines"""
    matcher = re.compile((
        '''L\s{date_re}:\s(?P<source_user>".*?")\sdisconnected \(reason '''
        '''"(?P<text>.*?)"\)'''
    ).format(**patterns))

    def parse(self, result):
        values = result.groupdict()
        self.parse_timestamp(**values)
        self.source = User(values["source_user"])
        self.text = values["text"]

with open('match.log') as f:
    for line in f.readlines():
        result = Line.identify(line)
        if not result.matched:
            print line.strip()
