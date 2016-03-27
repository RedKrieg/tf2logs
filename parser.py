#!/usr/bin/env python

import datetime
import re

patterns = {
    "user_re": '''"(?P<username>.*?)<(?P<server_id>\d+)>'''
               '''<(?P<steam_id>\[(?:[UIMGAPCgTcLa]:[0-4]:\d+)\]|BOT|Console)>'''
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
        self.player_class = None

    def __repr__(self):
        attrs = self.__dict__
        attr_reprs = [ "{}={!r}".format(k, v) for k, v in attrs.iteritems() ]
        attrs_str = ", ".join(attr_reprs)
        return "{}({})".format(self.__class__.__name__, attrs_str)

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

    def __repr__(self):
        attrs = self.__dict__
        attr_reprs = [ "{}={!r}".format(k, v) for k, v in attrs.iteritems() ]
        attrs_str = ", ".join(attr_reprs)
        return "{}({})".format(self.__class__.__name__, attrs_str)

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
        for subclass in set(cls.find_children()):
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

class TimeLine(Line):
    """Lines that have a timestamp"""
    def parse(self, result):
        values = result.groupdict()
        self.parse_timestamp(**values)

class TeamLine(TimeLine):
    """Lines that have a team attribute"""
    def parse(self, result):
        values = result.groupdict()
        self.parse_timestamp(**values)
        self.team = values["team"]

class TextLine(TimeLine):
    """Lines that have a text attribute"""
    def parse(self, result):
        values = result.groupdict()
        self.parse_timestamp(**values)
        self.text = values["text"]

class SourceLine(TimeLine):
    """Lines with a source"""
    def parse(self, result):
        values = result.groupdict()
        self.parse_timestamp(**values)
        self.source = User(values["source_user"])

class SourceClassLine(SourceLine):
    """Lines with source and class"""
    def parse(self, result):
        values = result.groupdict()
        self.parse_timestamp(**values)
        self.source = User(values["source_user"])
        self.source.player_class = values["class"]

class SourceTeamLine(SourceLine, TeamLine):
    """Lines with source and team attributes"""
    def parse(self, result):
        values = result.groupdict()
        self.parse_timestamp(**values)
        self.source = User(values["source_user"])
        self.team = values["team"]
        self.source.team = self.team

class SourceTextLine(SourceLine, TextLine):
    """Lines with source and text attributes"""
    def parse(self, result):
        values = result.groupdict()
        self.parse_timestamp(**values)
        self.source = User(values["source_user"])
        self.text = values["text"]

class DataLine(TimeLine):
    """Lines that have a timestamp and "data" group"""
    def parse(self, result):
        values = result.groupdict()
        self.parse_timestamp(**values)
        self.data = self.parse_values(values["data"])

class SourceDataLine(DataLine, SourceLine):
    """Lines with a source and data"""
    def parse(self, result):
        values = result.groupdict()
        self.parse_timestamp(**values)
        self.source = User(values["source_user"])
        self.data = self.parse_values(values["data"])

class TeamDataLine(TeamLine, DataLine):
    """Lines with team and data attributes"""
    def parse(self, result):
        values = result.groupdict()
        self.parse_timestamp(**values)
        self.team = values["team"]
        self.data = self.parse_values(values["data"])

class TextDataLine(TextLine, DataLine):
    """Lines with text and data attributes"""
    def parse(self, result):
        values = result.groupdict()
        self.parse_timestamp(**values)
        self.text = values["text"]
        self.data = self.parse_values(values["data"])

class TeamTextDataLine(TextDataLine, TeamDataLine):
    """Lines with text, team, and data attributes"""
    def parse(self, result):
        values = result.groupdict()
        self.parse_timestamp(**values)
        self.text = values["text"]
        self.team = values["team"]
        self.data = self.parse_values(values["data"])

class SourceWeaponDataLine(SourceDataLine):
    """Lines with source, weapon, and data"""
    def parse(self, result):
        values = result.groupdict()
        self.parse_timestamp(**values)
        self.source = User(values["source_user"])
        self.weapon = values["weapon"]
        self.data = self.parse_values(values["data"])

class SourceTargetLine(SourceLine):
    """Lines with source and target"""
    def parse(self, result):
        values = result.groupdict()
        self.parse_timestamp(**values)
        self.source = User(values["source_user"])
        self.target = User(values["target_user"])

class SourceTargetDataLine(SourceTargetLine, SourceDataLine):
    """Lines with sources, targets, and data"""
    def parse(self, result):
        values = result.groupdict()
        self.parse_timestamp(**values)
        self.source = User(values["source_user"])
        self.target = User(values["target_user"])
        self.data = self.parse_values(values["data"])

class SourceTargetWeaponDataLine(SourceTargetDataLine):
    """Like SourceTargetDataLine but also has a weapon attribute"""
    def parse(self, result):
        values = result.groupdict()
        self.parse_timestamp(**values)
        self.source = User(values["source_user"])
        self.target = User(values["target_user"])
        self.weapon = values["weapon"]
        self.data = self.parse_values(values["data"])

class LogStartLine(DataLine):
    """Matches start of log"""
    matcher = re.compile(
        '''L\s{date_re}:\sLog file started(?P<data>(?:\s{data_re})*)$'''.format(
            **patterns
        )
    )

class LogEndLine(TimeLine):
    """Matches end of log"""
    matcher = re.compile(
        '''L\s{date_re}:\sLog file closed.$'''.format(**patterns)
    )


class ServerMessageLine(TextLine):
    """Matches server messages"""
    matcher = re.compile(
        '''L\s{date_re}:\sserver_message: "(?P<text>.*?)"$'''.format(**patterns)
    )

class ServerCvarLine(DataLine):
    """Matches server cvar states"""
    matcher = re.compile(
        '''L\s{date_re}:\s"(?P<key>.*?)" = "(?P<value>.*?)"$'''.format(**patterns)
    )

    def parse(self, result):
        values = result.groupdict()
        self.parse_timestamp(**values)
        self.data = { values["key"]: values["value"] }

class ServerCvarSetLine(ServerCvarLine):
    """Matches server cvar changes"""
    matcher = re.compile(
        '''L\s{date_re}:\sserver_cvar: "(?P<key>.*?)" "(?P<value>.*?)"$'''.format(**patterns)
    )

class LoadMapLine(TextLine):
    """Matches loading map lines"""
    matcher = re.compile(
        '''L\s{date_re}:\sLoading map "(?P<text>.*?)"$'''.format(**patterns)
    )

class RconLine(DataLine):
    """Matches an rcon command"""
    matcher = re.compile(
        '''L\s{date_re}:\srcon from "(?P<source>.*?)": command "(?P<command>.*?)"$'''.format(**patterns)
    )

    def parse(self, result):
        values = result.groupdict()
        self.parse_timestamp(**values)
        self.data = {
            "source": values["source"],
            "command": values["command"]
        }

class TournamentModeLine(TimeLine):
    """Matches the beginning of tournament mode"""
    matcher = re.compile(
        '''L\s{date_re}:\sTournament mode started$'''.format(**patterns)
    )

class TeamNameLine(TeamLine):
    """Matches team name in tournament mode"""
    matcher = re.compile('''(?P<team>Red|Blue) Team: (?P<name>.*)$''')

    def parse(self, result):
        values = result.groupdict()
        self.timestamp = None
        self.team = values["team"]
        self.name = values["name"]

class SayLine(SourceTextLine):
    """Matches say lines"""
    matcher = re.compile(
        '''L\s{date_re}:\s(?P<source_user>{user_re})\ssay\s"(?P<text>.*)"$'''.format(
            **patterns
        )
    )

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

class PlayerConnectedLine(SourceTextLine):
    """Matches a player connecting to the server"""
    matcher = re.compile(
        '''L\s{date_re}:\s(?P<source_user>{user_re})\sconnected, address "(?P<text>.*)"$'''.format(
            **patterns
        )
    )

class PlayerValidatedLine(SourceLine):
    """Matches a user getting validated"""
    matcher = re.compile(
        '''L\s{date_re}:\s(?P<source_user>{user_re})\sSTEAM USERID validated$'''.format(
            **patterns
        )
    )

class PlayerEnterGameLine(SourceLine):
    """Matches a player entering the game"""
    matcher = re.compile(
        '''L\s{date_re}:\s(?P<source_user>{user_re})\sentered the game$'''.format(
            **patterns
        )
    )

class PlayerJoinTeamLine(SourceTeamLine):
    """Matches a player joining a team"""
    matcher = re.compile(
        '''L\s{date_re}:\s(?P<source_user>{user_re})\sjoined team "(?P<text>.*)"$'''.format(**patterns)
    )

class PlayerChangeClassLine(SourceClassLine):
    """Matches a player changing classes"""
    matcher = re.compile(
        '''L\s{date_re}:\s(?P<source_user>{user_re})\schanged role to "(?P<class>.*)"$'''.format(**patterns)
    )

class PlayerChangeNameLine(SourceTextLine):
    """Matches a player name change event"""
    matcher = re.compile(
        '''L\s{date_re}:\s(?P<source_user>{user_re})\schanged name to "(?P<text>.*)"$'''.format(**patterns)
    )

class DamagePlayerTriggerLine(SourceTargetDataLine):
    """Matches when damage is triggered on a player"""
    matcher = re.compile((
        '''L\s{date_re}:\s(?P<source_user>".*?")\striggered "damage" '''
        '''against (?P<target_user>".*?")(?P<data>(?:\s{data_re})*)$'''
    ).format(**patterns))

class KillLine(SourceTargetWeaponDataLine):
    """Matches when a player kills another player"""
    matcher = re.compile((
        '''L\s{date_re}:\s(?P<source_user>".*?")\skilled\s'''
        '''(?P<target_user>".*?")\swith\s"(?P<weapon>.*?)"'''
        '''(?P<data>(?:\s{data_re})*)'''
    ).format(**patterns))

class KillAssistLine(SourceTargetDataLine):
    """Matches when a player gets a kill assist"""
    matcher = re.compile((
        '''L\s{date_re}:\s(?P<source_user>".*?")\striggered "kill assist"'''
        ''' against (?P<target_user>".*?")(?P<data>(?:\s{data_re})*)$'''
    ).format(**patterns))

class SuicideLine(SourceWeaponDataLine):
    """Matches when a player suicides"""
    matcher = re.compile((
        '''L\s{date_re}:\s(?P<source_user>".*?")\scommitted suicide with '''
        '''"(?P<weapon>.*?)"(?P<data>(?:\s{data_re})*)$'''
    ).format(**patterns))

    def parse(self, result):
        values = result.groupdict()
        self.parse_timestamp(**values)
        self.source = User(values["source_user"])
        self.weapon = values["weapon"]
        self.data = self.parse_values(values["data"])

class WorldTriggerLine(TextDataLine):
    """Matches world triggers"""
    matcher = re.compile((
        '''L\s{date_re}:\sWorld triggered "(?P<text>.*?)"'''
        '''(?P<data>(?:\s{data_re})*)$'''
    ).format(**patterns))

class TeamStatusLine(TeamDataLine):
    """Matches team status lines"""
    matcher = re.compile((
        '''L\s{date_re}:\sTeam "(?P<team>.*?)" current score "(?P<score>\d+)'''
        '''" with "(?P<player_count>\d+)" players$'''
    ).format(**patterns))

    def parse(self, result):
        values = result.groupdict()
        self.parse_timestamp(**values)
        self.team = values["team"]
        self.data = {
            "score": values["score"],
            "player_count": values["player_count"]
        }

class CapturePointLine(TeamDataLine):
    """Matches team capture lines"""
    matcher = re.compile((
        '''L\s{date_re}:\sTeam "(?P<team>.*?)" triggered "pointcaptured"'''
        '''(?P<data>(?:\s{data_re})*)$'''
    ).format(**patterns))

class ItemPickUpLine(TeamTextDataLine):
    """Matches item pickups"""
    matcher = re.compile((
        '''L\s{date_re}:\s(?P<source_user>".*?")\spicked up item "'''
        '''(?P<text>.*?)"(?P<data>(?:\s{data_re})*)$'''
    ).format(**patterns))

    def parse(self, result):
        values = result.groupdict()
        self.parse_timestamp(**values)
        self.source = User(values["source_user"])
        self.text = values["text"]
        self.data = self.parse_values(values["data"])

class HealTriggerLine(SourceTargetDataLine):
    """Matches healing lines"""
    matcher = re.compile((
        '''L\s{date_re}:\s(?P<source_user>".*?")\striggered "healed" '''
        '''against (?P<target_user>".*?")(?P<data>(?:\s{data_re})*)$'''
    ).format(**patterns))

class ChargeReadyTriggerLine(SourceDataLine):
    """Matches uber deploy lines"""
    matcher = re.compile((
        '''L\s{date_re}:\s(?P<source_user>".*?")\striggered '''
        '''"chargeready"(?P<data>(?:\s{data_re})*)$'''
    ).format(**patterns))

class ChargeDeployTriggerLine(SourceDataLine):
    """Matches uber deploy lines"""
    matcher = re.compile((
        '''L\s{date_re}:\s(?P<source_user>".*?")\striggered '''
        '''"chargedeployed"(?P<data>(?:\s{data_re})*)$'''
    ).format(**patterns))

class ChargeEndedTriggerLine(SourceDataLine):
    """Matches uber deploy lines"""
    matcher = re.compile((
        '''L\s{date_re}:\s(?P<source_user>".*?")\striggered '''
        '''"chargeended"(?P<data>(?:\s{data_re})*)$'''
    ).format(**patterns))

class UberEmptyTriggerLine(SourceDataLine):
    """Matches uber empty lines"""
    matcher = re.compile((
        '''L\s{date_re}:\s(?P<source_user>".*?")\striggered '''
        '''"empty_uber"(?P<data>(?:\s{data_re})*)$'''
    ).format(**patterns))

class UberAdvantageLostTriggerLine(SourceDataLine):
    """Matches when uber advantage is lost"""
    matcher = re.compile((
        '''L\s{date_re}:\s(?P<source_user>".*?")\striggered '''
        '''"lost_uber_advantage"(?P<data>(?:\s{data_re})*)$'''
    ).format(**patterns))

class MedicDeathTrigger(SourceTargetDataLine):
    """Matches when medic deaths are recorded"""
    matcher = re.compile((
        '''L\s{date_re}:\s(?P<source_user>".*?")\striggered '''
        '''"medic_death" against (?P<target_user>".*?")(?P<data>(?:\s{data_re})*)$'''
    ).format(**patterns))

class MedicDeathExTrigger(SourceDataLine):
    """Matches when medic deaths are recorded again?"""
    matcher = re.compile((
        '''L\s{date_re}:\s(?P<source_user>".*?")\striggered '''
        '''"medic_death_ex"(?P<data>(?:\s{data_re})*)$'''
    ).format(**patterns))

class FirstHealAfterSpawnTrigger(SourceDataLine):
    """Matches when medic heals after spawning"""
    matcher = re.compile((
        '''L\s{date_re}:\s(?P<source_user>".*?")\striggered '''
        '''"first_heal_after_spawn"(?P<data>(?:\s{data_re})*)$'''
    ).format(**patterns))

class PlayerExtinguishedTriggerLine(SourceTargetWeaponDataLine):
    """Matches extinguish lines"""
    matcher = re.compile((
        '''L\s{date_re}:\s(?P<source_user>".*?")\striggered '''
        '''"player_extinguished" against (?P<target_user>".*?")'''
        ''' with "(?P<weapon>.*?)"(?P<data>(?:\s{data_re})*)$'''
    ).format(**patterns))

class JarateAttackTriggerLine(SourceTargetWeaponDataLine):
    """Matches jarate_attack"""
    matcher = re.compile((
        '''L\s{date_re}:\s(?P<source_user>".*?")\striggered '''
        '''"jarate_attack" against (?P<target_user>".*?")'''
        ''' with "(?P<weapon>.*?)"(?P<data>(?:\s{data_re})*)$'''
    ).format(**patterns))

class MilkAttackTriggerLine(SourceTargetWeaponDataLine):
    """Matches milk_attack"""
    matcher = re.compile((
        '''L\s{date_re}:\s(?P<source_user>".*?")\striggered '''
        '''"milk_attack" against (?P<target_user>".*?")'''
        ''' with "(?P<weapon>.*?)"(?P<data>(?:\s{data_re})*)$'''
    ).format(**patterns))

class KillObjectLine(SourceDataLine):
    """Matches 'killedobject' lines"""
    matcher = re.compile((
        '''L\s{date_re}:\s(?P<source_user>".*?")\striggered '''
        '''"killedobject"(?P<data>(?:\s{data_re})*)$'''
    ).format(**patterns))

class SpawnLine(SourceClassLine):
    """Matches 'spawned' lines"""
    matcher = re.compile((
        '''L\s{date_re}:\s(?P<source_user>".*?")\sspawned as "'''
        '''(?P<class>.*?)"$'''
    ).format(**patterns))

class PlayerBuiltObjectTriggerLine(SourceDataLine):
    """Matches building lines"""
    matcher = re.compile((
        '''L\s{date_re}:\s(?P<source_user>".*?")\striggered '''
        '''"player_builtobject"(?P<data>(?:\s{data_re})*)$'''
    ).format(**patterns))

class PlayerCarryObjectTriggerLine(SourceDataLine):
    """Matches player carrying objects"""
    matcher = re.compile((
        '''L\s{date_re}:\s(?P<source_user>".*?")\striggered '''
        '''"player_carryobject"(?P<data>(?:\s{data_re})*)$'''
    ).format(**patterns))

class PlayerDropObjectTriggerLine(SourceDataLine):
    """Matches a player dropping an object"""
    matcher = re.compile((
        '''L\s{date_re}:\s(?P<source_user>".*?")\striggered '''
        '''"player_dropobject"(?P<data>(?:\s{data_re})*)$'''
    ).format(**patterns))

class ObjectDetonatedTriggerLine(SourceDataLine):
    """Matches a player detonating an object"""
    matcher = re.compile((
        '''L\s{date_re}:\s(?P<source_user>".*?")\striggered '''
        '''"object_detonated"(?P<data>(?:\s{data_re})*)$'''
    ).format(**patterns))

class DominationTriggerLine(SourceTargetDataLine):
    """Matches domination lines"""
    matcher = re.compile((
        '''L\s{date_re}:\s(?P<source_user>".*?")\striggered '''
        '''"domination" against (?P<target_user>".*?")'''
        '''(?P<data>(?:\s{data_re})*)$'''
    ).format(**patterns))

class RevengeTriggerLine(SourceTargetDataLine):
    """Matches revenge lines"""
    matcher = re.compile((
        '''L\s{date_re}:\s(?P<source_user>".*?")\striggered '''
        '''"revenge" against (?P<target_user>".*?")'''
        '''(?P<data>(?:\s{data_re})*)$'''
    ).format(**patterns))

class CaptureBlockedTriggerLine(SourceDataLine):
    """Matches capture point blocked lines"""
    matcher = re.compile((
        '''L\s{date_re}:\s(?P<source_user>".*?")\striggered '''
        '''"captureblocked"(?P<data>(?:\s{data_re})*)$'''
    ).format(**patterns))

class PlayerDisconnectedLine(SourceDataLine):
    """Matches player disconnect lines"""
    matcher = re.compile((
        '''L\s{date_re}:\s(?P<source_user>".*?")\sdisconnected'''
        '''(?P<data>(?:\s{data_re})*)$'''
    ).format(**patterns))
