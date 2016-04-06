# -*- coding: UTF-8 -*-
import collections
import datetime
import functools
import re
import timeseries

patterns = {
    "user_re": '''"(?P<username>.*?)<(?P<server_id>\d+)>'''
               '''<(?P<steam_id>\[(?:[UIMGAPCgTcLa]:[0-4]:\d+)\]|BOT|Console)>'''
               '''<(?P<team>\w*)>"''',
    "date_re": '''(?P<month>\d\d)/(?P<day>\d\d)/(?P<year>\d+)\s'''
               '''-\s(?P<hour>\d\d):(?P<minute>\d\d):(?P<second>\d\d)''',
    "item_re": '''\((?P<name>\w+)\s"(?P<value>.*?)"\)''',
    "source_re": '''(?P<source_user>".*?")''',
    "target_re": '''(?P<target_user>".*?")''',
    "weapon_re": '''"(?P<weapon>.*?)"''',
    "text_re": '''"(?P<text>.*?)"''',
    "team_re": '''"(?P<team>.*?)"'''
}
patterns["data_re"] = '''(?P<data>(?:\s{item_re})*)\s*$'''.format(**patterns)

class_icons = {
    "Sniper": "⌖",
    "Spy": "🔪",
    "Demoman": "💣",
    "Heavy": "🍫",
    "Soldier": "🚀",
    "Engineer": "🔧",
    "Medic": "✚",
    "Scout": "👟",
    "Pyro": "🔥"
}

class World:
    """Represents the game world"""
    def __init__(self):
        self.known_users = {}
        self.filename = ""
        self.mapname = ""
        self.team_names = {
            "Red": "RED",
            "Blue": "BLU"
        }

    def __repr__(self):
        attrs = {
            "filename": self.filename,
            "mapname": self.mapname,
            "team_names": self.team_names
        }
        attr_reprs = [ "{}={!r}".format(k, v) for k, v in attrs.items() ]
        attrs_str = ", ".join(attr_reprs)
        return "{}({})".format(self.__class__.__name__, attrs_str)

    def user_lookup(self, user_text):
        user = User(user_text)
        if not user.valid:
            return user
        if user.steam_id in self.known_users:
            known_user = self.known_users[user.steam_id]
            known_user.update(user)
            known_user.counters["seen"][self.timestamp] = 1
            return known_user
        else:
            self.known_users[user.steam_id] = user
            return user

    def get_user_by_steam_id(self, steam_id):
        if steam_id in self.known_users:
            return self.known_users[steam_id]
        return User(steam_id) # invalid

    def read_log_from_file(self, filename):
        with open('serverfiles/tf/logs/{}'.format(filename)) as f:
            for line in f.readlines():
                result = Line.identify(self, line)
                if result.matched:
                    yield result
                else:
                    pass # log here

class User:
    """Represents a User"""
    known_users = {}
    def __init__(self, user_text, interval=10):
        """<user_text> is anything that will match user_re successfully.
        The 'valid' attribute indicates whether or not the constructor
        was successful."""
        match = re.match(patterns["user_re"], user_text)
        self.valid = match is not None
        if not self.valid:
            return
        user_data = match.groupdict()
        self.name = user_data["username"]
        self.steam_id = user_data["steam_id"]
        self.team = user_data["team"]
        self.original_team = self.team
        self.server_id = user_data["server_id"]
        self.player_class = None
        self.played_classes = set()
        self.interval = interval
        self.reset_counters()

    def __repr__(self):
        if not self.valid:
            return "{}({})".format(self.__class__.__name__, "valid=False")
        attrs = {
            "name": self.name,
            "steam_id": self.steam_id,
            "player_class": self.player_class,
            "server_id": self.server_id,
            "team": self.team
        }
        attr_reprs = [ "{}={!r}".format(k, v) for k, v in attrs.items() ]
        attrs_str = ", ".join(attr_reprs)
        return "{}({})".format(self.__class__.__name__, attrs_str)

    def __str__(self):
        return "{name}<{server_id}><{steam_id}><{team}>".format(**self.__dict__)

    def __format__(self, format_spec):
        player_symbol = class_icons.get(self.player_class, "?")
        return "{} - {}".format(
            player_symbol, self.name
        ).__format__(format_spec)

    def team_class(self):
        return "{original_team} {player_class}".format(**self.__dict__)

    def reset_counters(self):
        # This creates a class constructor for defaultdict where the default
        # value is an instance of SparseTimeSeries with the resolver kwarg set
        # to add on duplicate key (aggregator function)
        single_counter = functools.partial(
            timeseries.SparseTimeSeries,
            aggregator=lambda o, n: o+n,
            interval=self.interval
        )
        multi_counter = functools.partial(
            collections.defaultdict,
            single_counter
        )
        self.counters = {
            "seen": single_counter(),
            "kills": multi_counter(),
            "assists": multi_counter(),
            "constructions": multi_counter(),
            "destructions": multi_counter(),
            "damage": multi_counter(),
            "damage_by_weapon": multi_counter(),
            "realdamage": multi_counter(),
            "realdamage_by_weapon": multi_counter(),
            "damage_received": multi_counter(),
            "deaths": multi_counter(),
            "heals_given": multi_counter(),
            "heals_received": multi_counter(),
            "suicides": single_counter(),
            "med_picks": multi_counter(),
            "points_captured": single_counter(),
            "points_blocked": single_counter(),
            "dominations": multi_counter(),
            "revenges": multi_counter(),
            "headshots": multi_counter(),
            "airshots": multi_counter(),
            "headshot_kills": multi_counter(),
            "backstab_kills": multi_counter(),
            "extinguishes": multi_counter(),
            "feigns": multi_counter(),
            "feigns_triggered": multi_counter()
        }

    def get_counter_totals(self, counter):
        """Gets the total value timeseries data for [counter].

        All SparseTimeSeries instances must have the same start and end times
        """
        my_counter = self.counters[counter]
        if isinstance(my_counter, timeseries.SparseTimeSeries):
            return my_counter.items()
        try:
            timestamps = next(tseries.keys() for tseries in my_counter.values())
        except StopIteration:
            return []
        values = (
            sum(v) for v in zip(
                *[
                    tseries.values() for tseries in my_counter.values()
                ]
            )
        )
        return zip(timestamps, values)

    def set_counter_durations(self, start, end):
        """Sets the start and end times for each counter"""
        for value in self.counters.values():
            if isinstance(value, timeseries.SparseTimeSeries):
                value.set_start(start)
                value.set_end(end)
            elif isinstance(value, dict):
                for multi_value in value.values():
                    multi_value.set_start(start)
                    multi_value.set_end(end)

    def update(self, other):
        self.name = other.name
        if self.original_team not in ('Blue', 'Red'):
            self.original_team = other.team
        self.team = other.team
        self.server_id = self.server_id

    def update_class(self, player_class):
        self.played_classes.add(player_class)
        self.player_class = player_class

class Line:
    """Represents a line in the log.  Base class.
    Constructor requires a World instance and the text line."""
    matcher = re.compile("$") # empty line for base class

    def __init__(self, world, line):
        result = self.matcher.match(line)
        self.matched = result is not None
        self.world = world
        if self.matched:
            self.parse(result)
            if hasattr(self, 'update_world'):
                self.update_world()

    def __repr__(self):
        attrs = self.__dict__
        attr_reprs = [ "{}={!r}".format(k, v) for k, v in attrs.items() ]
        attrs_str = ", ".join(attr_reprs)
        return "{}({})".format(self.__class__.__name__, attrs_str)

    def parse_timestamp(self, year, month, day, hour, minute, second, **kwargs):
        """Parses a timestamp from kwargs.
           Meant to be passed with **values"""
        self.timestamp = datetime.datetime(
            *( int(v) for v in (year, month, day, hour, minute, second) )
        )
        self.world.timestamp = self.timestamp

    @classmethod
    def find_children(cls):
        # http://stackoverflow.com/a/3862957
        return cls.__subclasses__() + [g for s in cls.__subclasses__()
                                       for g in s.find_children()]

    @classmethod
    def identify(cls, world, line):
        """Returns an instance of a subclass of Line that matches line, or Line that does not match"""
        for subclass in set(cls.find_children()):
            result = subclass(world, line)
            if result.matched:
                return result
        return cls(world, line)

    def parse(self, result):
        """Empty dictionary"""
        self.timestamp = None
        self.data = result.groupdict()

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
        self.source = self.world.user_lookup(values["source_user"])

class SourceClassLine(SourceLine):
    """Lines with source and class"""
    def parse(self, result):
        values = result.groupdict()
        self.parse_timestamp(**values)
        self.source = self.world.user_lookup(values["source_user"])
        self.source.update_class(values["class"])

class SourceTeamLine(SourceLine, TeamLine):
    """Lines with source and team attributes"""
    def parse(self, result):
        values = result.groupdict()
        self.parse_timestamp(**values)
        self.source = self.world.user_lookup(values["source_user"])
        self.team = values["team"]
        self.source.team = self.team

class SourceTextLine(SourceLine, TextLine):
    """Lines with source and text attributes"""
    def parse(self, result):
        values = result.groupdict()
        self.parse_timestamp(**values)
        self.source = self.world.user_lookup(values["source_user"])
        self.text = values["text"]

class DataLine(TimeLine):
    """Lines that have a timestamp and "data" group"""
    def parse(self, result):
        values = result.groupdict()
        self.parse_timestamp(**values)
        self.data = self.parse_values(values["data"])

    def parse_values(self, values_string):
        data = dict(re.findall(patterns["item_re"], values_string))
        return self.coerce_data(data)

    def coerce_data(self, data):
        """Attempt to convert strings to more useful types"""
        coerced_data = {}
        for key, value in data.items():
            if type(value) is not str:
                continue
            try:
                coerced_data[key] = int(value)
                continue
            except ValueError:
                pass
            try:
                coerced_data[key] = float(value)
                continue
            except ValueError:
                pass
            try: # some floats have 'f' on the end, "0.5f"
                if type(value) is str and value.endswith('f'):
                    coerced_data[key] = float(value[:-1])
                    continue
            except ValueError:
                pass
            user = self.world.user_lookup('''"{}"'''.format(value))
            if user.valid:
                coerced_data[key] = user
            coords = value.split()
            if len(coords) == 3:
                try:
                    coerced_data[key] = tuple( int(c) for c in coords )
                    continue
                except ValueError:
                    pass
        data.update(coerced_data)
        return data

class SourceDataLine(DataLine, SourceLine):
    """Lines with a source and data"""
    def parse(self, result):
        values = result.groupdict()
        self.parse_timestamp(**values)
        self.source = self.world.user_lookup(values["source_user"])
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
        self.source = self.world.user_lookup(values["source_user"])
        self.weapon = values["weapon"]
        self.data = self.parse_values(values["data"])

class SourceTargetLine(SourceLine):
    """Lines with source and target"""
    def parse(self, result):
        values = result.groupdict()
        self.parse_timestamp(**values)
        self.source = self.world.user_lookup(values["source_user"])
        self.target = self.world.user_lookup(values["target_user"])

class SourceTargetDataLine(SourceTargetLine, SourceDataLine):
    """Lines with sources, targets, and data"""
    def parse(self, result):
        values = result.groupdict()
        self.parse_timestamp(**values)
        self.source = self.world.user_lookup(values["source_user"])
        self.target = self.world.user_lookup(values["target_user"])
        self.data = self.parse_values(values["data"])

class SourceTargetWeaponDataLine(SourceTargetDataLine):
    """Like SourceTargetDataLine but also has a weapon attribute"""
    def parse(self, result):
        values = result.groupdict()
        self.parse_timestamp(**values)
        self.source = self.world.user_lookup(values["source_user"])
        self.target = self.world.user_lookup(values["target_user"])
        self.weapon = values["weapon"]
        self.data = self.parse_values(values["data"])

class LogStartLine(DataLine):
    """Matches start of log"""
    matcher = re.compile(
        '''L\s{date_re}:\sLog file started{data_re}'''.format(
            **patterns
        )
    )
    def update_world(self):
        self.world.filename = self.data["file"]

class LogEndLine(TimeLine):
    """Matches end of log"""
    matcher = re.compile(
        '''L\s{date_re}:\sLog file closed.$'''.format(**patterns)
    )

class ServerMessageLine(TextLine):
    """Matches server messages"""
    matcher = re.compile(
        '''L\s{date_re}:\sserver_message: {text_re}$'''.format(**patterns)
    )

class ServerCvarLine(DataLine):
    """Matches server cvar states"""
    matcher = re.compile(
        '''L\s{date_re}:\s"(?P<key>.*?)" = "(?P<value>.*?)"$'''.format(**patterns)
    )

    def parse(self, result):
        values = result.groupdict()
        self.parse_timestamp(**values)
        self.data = self.coerce_data({ values["key"]: values["value"] })

class ServerCvarSetLine(ServerCvarLine):
    """Matches server cvar changes"""
    matcher = re.compile(
        '''L\s{date_re}:\sserver_cvar: "(?P<key>.*?)" "(?P<value>.*?)"$'''.format(**patterns)
    )

class LoadMapLine(TextLine):
    """Matches loading map lines"""
    matcher = re.compile(
        '''L\s{date_re}:\sLoading map {text_re}$'''.format(**patterns)
    )
    def update_world(self):
        self.world.mapname = self.text

class StartMapLine(TextDataLine):
    """Matches map start lines"""
    matcher = re.compile(
        '''L\s{date_re}:\sStarted map {text_re}{data_re}'''.format(**patterns)
    )
    def update_world(self):
        self.world.mapname = self.text

class RconLine(DataLine):
    """Matches an rcon command"""
    matcher = re.compile(
        '''L\s{date_re}:\srcon from "(?P<source>.*?)": command "(?P<command>.*?)"$'''.format(**patterns)
    )

    def parse(self, result):
        values = result.groupdict()
        self.parse_timestamp(**values)
        self.data = self.coerce_data({
            "source": values["source"],
            "command": values["command"]
        })

class TournamentModeLine(TimeLine):
    """Matches the beginning of tournament mode"""
    matcher = re.compile(
        '''L\s{date_re}:\sTournament mode started$'''.format(**patterns)
    )
    def update_world(self):
        for user in self.world.known_users.values():
            user.reset_counters()
        self.world.first_timestamp = self.timestamp

class TeamNameLine(Line):
    """Matches team name in tournament mode"""
    matcher = re.compile('''(?P<team>Red|Blue) Team: (?P<name>.*)$''')

    def parse(self, result):
        values = result.groupdict()
        self.timestamp = None
        self.team = values["team"]
        self.name = values["name"]

    def update_world(self):
        self.world.team_names[self.team] = self.name

class SayLine(SourceTextLine):
    """Matches say lines"""
    matcher = re.compile(
        '''L\s{date_re}:\s{source_re}\ssay\s{text_re}$'''.format(
            **patterns
        )
    )

class SayTeamLine(SayLine):
    """Matches say_team lines"""
    matcher = re.compile(
        '''L\s{date_re}:\s{source_re}\ssay_team\s{text_re}$'''.format(
            **patterns
        )
    )

    def parse(self, result):
        super(self.__class__, self).parse(result)
        self.team = self.source.team

class PlayerConnectedLine(SourceTextLine):
    """Matches a player connecting to the server"""
    matcher = re.compile(
        '''L\s{date_re}:\s{source_re}\sconnected, address {text_re}$'''.format(
            **patterns
        )
    )

class PlayerValidatedLine(SourceLine):
    """Matches a user getting validated"""
    matcher = re.compile(
        '''L\s{date_re}:\s{source_re}\sSTEAM USERID validated$'''.format(
            **patterns
        )
    )

class PlayerEnterGameLine(SourceLine):
    """Matches a player entering the game"""
    matcher = re.compile(
        '''L\s{date_re}:\s{source_re}\sentered the game$'''.format(
            **patterns
        )
    )

class PlayerJoinTeamLine(SourceTeamLine):
    """Matches a player joining a team"""
    matcher = re.compile(
        '''L\s{date_re}:\s{source_re}\sjoined team {team_re}$'''.format(**patterns)
    )

class PlayerChangeClassLine(SourceClassLine):
    """Matches a player changing classes"""
    matcher = re.compile(
        '''L\s{date_re}:\s{source_re}\schanged role to "(?P<class>.*)"$'''.format(**patterns)
    )

class PlayerChangeNameLine(SourceTextLine):
    """Matches a player name change event"""
    matcher = re.compile(
        '''L\s{date_re}:\s{source_re}\schanged name to {text_re}$'''.format(**patterns)
    )

class DamagePlayerTriggerLine(SourceTargetDataLine):
    """Matches when damage is triggered on a player"""
    matcher = re.compile((
        '''L\s{date_re}:\s{source_re}\striggered "damage" '''
        '''against {target_re}{data_re}'''
    ).format(**patterns))

    def update_world(self):
        self.source.counters["damage"][self.target][self.timestamp] = self.data["damage"]
        self.source.counters["damage_by_weapon"][self.data["weapon"]][self.timestamp] = self.data["damage"]
        if "realdamage" in self.data:
            self.source.counters["realdamage"][self.target][self.timestamp] = self.data["realdamage"]
            self.target.counters["damage_received"][self.source][self.timestamp] = self.data["realdamage"]
            self.source.counters["realdamage_by_weapon"][self.data["weapon"]][self.timestamp] = self.data["realdamage"]
        else:
            self.source.counters["realdamage"][self.target][self.timestamp] = self.data["damage"]
            self.target.counters["damage_received"][self.source][self.timestamp] = self.data["damage"]
            self.source.counters["realdamage_by_weapon"][self.data["weapon"]][self.timestamp] = self.data["damage"]
        if "headshot" in self.data:
            self.source.counters["headshots"][self.target][self.timestamp] = 1
        if "airshot" in self.data:
            self.source.counters["airshots"][self.target][self.timestamp] = 1

class KillLine(SourceTargetWeaponDataLine):
    """Matches when a player kills another player"""
    matcher = re.compile((
        '''L\s{date_re}:\s{source_re}\skilled\s'''
        '''{target_re}\swith\s{weapon_re}'''
        '''{data_re}'''
    ).format(**patterns))

    def update_world(self):
        if "customkill" in self.data:
            if self.data["customkill"] == "feign_death":
                self.source.counters["feigns_triggered"][self.target][self.timestamp] = 1
                self.target.counters["feigns"][self.source][self.timestamp] = 1
                return
            if self.data["customkill"] == "headshot":
                self.source.counters["headshot_kills"][self.target][self.timestamp] = 1
            elif self.data["customkill"] == "backstab":
                self.source.counters["backstab_kills"][self.target][self.timestamp] = 1
        self.source.counters["kills"][self.target][self.timestamp] = 1
        self.target.counters["deaths"][self.source][self.timestamp] = 1
        if self.target.player_class == "Medic":
            self.source.counters["med_picks"][self.target][self.timestamp] = 1

class KillAssistLine(SourceTargetDataLine):
    """Matches when a player gets a kill assist"""
    matcher = re.compile((
        '''L\s{date_re}:\s{source_re}\striggered "kill assist"'''
        ''' against {target_re}{data_re}'''
    ).format(**patterns))

    def update_world(self):
        self.source.counters["assists"][self.target][self.timestamp] = 1

class SuicideLine(SourceWeaponDataLine):
    """Matches when a player suicides"""
    matcher = re.compile((
        '''L\s{date_re}:\s{source_re}\scommitted suicide with '''
        '''{weapon_re}{data_re}'''
    ).format(**patterns))

    def parse(self, result):
        values = result.groupdict()
        self.parse_timestamp(**values)
        self.source = self.world.user_lookup(values["source_user"])
        self.weapon = values["weapon"]
        self.data = self.parse_values(values["data"])

    def update_world(self):
        self.source.counters["suicides"][self.timestamp] = 1

class WorldTriggerLine(TextDataLine):
    """Matches world triggers"""
    matcher = re.compile((
        '''L\s{date_re}:\sWorld triggered {text_re}'''
        '''{data_re}'''
    ).format(**patterns))

    def update_world(self):
        self.world.last_timestamp = self.timestamp

class TeamStatusLine(TeamDataLine):
    """Matches team status lines"""
    matcher = re.compile((
        '''L\s{date_re}:\sTeam {team_re} current score "(?P<score>\d+)'''
        '''" with "(?P<player_count>\d+)" players$'''
    ).format(**patterns))

    def parse(self, result):
        values = result.groupdict()
        self.parse_timestamp(**values)
        self.team = values["team"]
        self.data = self.coerce_data({
            "score": values["score"],
            "player_count": values["player_count"]
        })

class TeamFinalLine(TeamStatusLine):
    """Matches team final score lines"""
    matcher = re.compile((
        '''L\s{date_re}:\sTeam {team_re} final score "(?P<score>\d+)'''
        '''" with "(?P<player_count>\d+)" players$'''
    ).format(**patterns))

class CapturePointLine(TeamDataLine):
    """Matches team capture lines"""
    matcher = re.compile((
        '''L\s{date_re}:\sTeam {team_re} triggered "pointcaptured"'''
        '''{data_re}'''
    ).format(**patterns))

    def update_world(self):
        for key, value in self.data.items():
            if not key.startswith("player"):
                continue
            value.counters["points_captured"][self.timestamp] = 1

class ItemPickUpLine(TeamTextDataLine):
    """Matches item pickups"""
    matcher = re.compile((
        '''L\s{date_re}:\s{source_re}\spicked up item '''
        '''{text_re}{data_re}'''
    ).format(**patterns))

    def parse(self, result):
        values = result.groupdict()
        self.parse_timestamp(**values)
        self.source = self.world.user_lookup(values["source_user"])
        self.text = values["text"]
        self.data = self.parse_values(values["data"])

class HealTriggerLine(SourceTargetDataLine):
    """Matches healing lines"""
    matcher = re.compile((
        '''L\s{date_re}:\s{source_re}\striggered "healed" '''
        '''against {target_re}{data_re}'''
    ).format(**patterns))

    def update_world(self):
        self.source.counters["heals_given"][self.target][self.timestamp] = self.data["healing"]
        self.target.counters["heals_received"][self.source][self.timestamp] = self.data["healing"]

class ChargeReadyTriggerLine(SourceDataLine):
    """Matches uber deploy lines"""
    matcher = re.compile((
        '''L\s{date_re}:\s{source_re}\striggered '''
        '''"chargeready"{data_re}'''
    ).format(**patterns))

class ChargeDeployTriggerLine(SourceDataLine):
    """Matches uber deploy lines"""
    matcher = re.compile((
        '''L\s{date_re}:\s{source_re}\striggered '''
        '''"chargedeployed"{data_re}'''
    ).format(**patterns))

class ChargeEndedTriggerLine(SourceDataLine):
    """Matches uber deploy lines"""
    matcher = re.compile((
        '''L\s{date_re}:\s{source_re}\striggered '''
        '''"chargeended"{data_re}'''
    ).format(**patterns))

class UberEmptyTriggerLine(SourceDataLine):
    """Matches uber empty lines"""
    matcher = re.compile((
        '''L\s{date_re}:\s{source_re}\striggered '''
        '''"empty_uber"{data_re}'''
    ).format(**patterns))

class UberAdvantageLostTriggerLine(SourceDataLine):
    """Matches when uber advantage is lost"""
    matcher = re.compile((
        '''L\s{date_re}:\s{source_re}\striggered '''
        '''"lost_uber_advantage"{data_re}'''
    ).format(**patterns))

class MedicDeathTrigger(SourceTargetDataLine):
    """Matches when medic deaths are recorded"""
    matcher = re.compile((
        '''L\s{date_re}:\s{source_re}\striggered '''
        '''"medic_death" against {target_re}{data_re}'''
    ).format(**patterns))

class MedicDeathExTrigger(SourceDataLine):
    """Matches when medic deaths are recorded again?"""
    matcher = re.compile((
        '''L\s{date_re}:\s{source_re}\striggered '''
        '''"medic_death_ex"{data_re}'''
    ).format(**patterns))

class FirstHealAfterSpawnTrigger(SourceDataLine):
    """Matches when medic heals after spawning"""
    matcher = re.compile((
        '''L\s{date_re}:\s{source_re}\striggered '''
        '''"first_heal_after_spawn"{data_re}'''
    ).format(**patterns))

class PlayerExtinguishedTriggerLine(SourceTargetWeaponDataLine):
    """Matches extinguish lines"""
    matcher = re.compile((
        '''L\s{date_re}:\s{source_re}\striggered '''
        '''"player_extinguished" against {target_re}'''
        ''' with {weapon_re}{data_re}'''
    ).format(**patterns))

    def update_world(self):
        self.source.counters["extinguishes"][self.target][self.timestamp] = 1

class JarateAttackTriggerLine(SourceTargetWeaponDataLine):
    """Matches jarate_attack"""
    matcher = re.compile((
        '''L\s{date_re}:\s{source_re}\striggered '''
        '''"jarate_attack" against {target_re}'''
        ''' with {weapon_re}{data_re}'''
    ).format(**patterns))

class MilkAttackTriggerLine(SourceTargetWeaponDataLine):
    """Matches milk_attack"""
    matcher = re.compile((
        '''L\s{date_re}:\s{source_re}\striggered '''
        '''"milk_attack" against {target_re}'''
        ''' with {weapon_re}{data_re}'''
    ).format(**patterns))

class KillObjectLine(SourceDataLine):
    """Matches 'killedobject' lines"""
    matcher = re.compile((
        '''L\s{date_re}:\s{source_re}\striggered '''
        '''"killedobject"{data_re}'''
    ).format(**patterns))

    def update_world(self):
        self.source.counters["destructions"][self.data["object"]][self.timestamp] = 1

class SpawnLine(SourceClassLine):
    """Matches 'spawned' lines"""
    matcher = re.compile((
        '''L\s{date_re}:\s{source_re}\sspawned as "'''
        '''(?P<class>.*?)"$'''
    ).format(**patterns))

class PlayerBuiltObjectTriggerLine(SourceDataLine):
    """Matches building lines"""
    matcher = re.compile((
        '''L\s{date_re}:\s{source_re}\striggered '''
        '''"player_builtobject"{data_re}'''
    ).format(**patterns))

    def update_world(self):
        self.source.counters["constructions"][self.data["object"]][self.timestamp] = 1

class PlayerCarryObjectTriggerLine(SourceDataLine):
    """Matches player carrying objects"""
    matcher = re.compile((
        '''L\s{date_re}:\s{source_re}\striggered '''
        '''"player_carryobject"{data_re}'''
    ).format(**patterns))

class PlayerDropObjectTriggerLine(SourceDataLine):
    """Matches a player dropping an object"""
    matcher = re.compile((
        '''L\s{date_re}:\s{source_re}\striggered '''
        '''"player_dropobject"{data_re}'''
    ).format(**patterns))

class ObjectDetonatedTriggerLine(SourceDataLine):
    """Matches a player detonating an object"""
    matcher = re.compile((
        '''L\s{date_re}:\s{source_re}\striggered '''
        '''"object_detonated"{data_re}'''
    ).format(**patterns))

class DominationTriggerLine(SourceTargetDataLine):
    """Matches domination lines"""
    matcher = re.compile((
        '''L\s{date_re}:\s{source_re}\striggered '''
        '''"domination" against {target_re}'''
        '''{data_re}'''
    ).format(**patterns))

    def update_world(self):
        self.source.counters["dominations"][self.target][self.timestamp] = 1

class RevengeTriggerLine(SourceTargetDataLine):
    """Matches revenge lines"""
    matcher = re.compile((
        '''L\s{date_re}:\s{source_re}\striggered '''
        '''"revenge" against {target_re}'''
        '''{data_re}'''
    ).format(**patterns))

    def update_world(self):
        self.source.counters["revenges"][self.target][self.timestamp] = 1

class CaptureBlockedTriggerLine(SourceDataLine):
    """Matches capture point blocked lines"""
    matcher = re.compile((
        '''L\s{date_re}:\s{source_re}\striggered '''
        '''"captureblocked"{data_re}'''
    ).format(**patterns))

    def update_world(self):
        self.source.counters["points_blocked"][self.timestamp] = 1

class PlayerDisconnectedLine(SourceDataLine):
    """Matches player disconnect lines"""
    matcher = re.compile((
        '''L\s{date_re}:\s{source_re}\sdisconnected'''
        '''{data_re}'''
    ).format(**patterns))
