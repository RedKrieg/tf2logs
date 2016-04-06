import datetime

class SparseTimeSeries:
    """A time series store with unique values every [interval] seconds.

    This class tracks the first and last timestamps recorded.  For any missing
    values at interval [interval], the default constructor of [datatype] will
    be returned (default int(), or 0).  The value for [interval] must always be
    of type 'int'.

    WARNING: Using keep_last_value=True will result in O(nlog(n)) iteration.

    Only objects of type 'datetime.datetime' are considered valid keys.  Every
    key will be converted to the earliest possible datetime within its interval
    before determining uniqueness.  By default, assignment to existing unique
    keys will replace the existing value with the new value.  To override this
    behavior, pass a function as [aggregator] which accepts two inputs, [old]
    and [new].  For example, to add values for an interval, you could use the
    following syntax:

    >>> ts = SparseTimeSeries(aggregator=lambda old, new: old + new)
    >>> now = datetime.datetime(2016, 4, 1, 17, 3, 44, 18797)
    >>> ts[now] = 1
    >>> ts[now] = 1
    >>> ts
    SparseTimeSeries({datetime.datetime(2016, 4, 1, 17, 3, 44): 2})
    """
    def __init__(
            self,
            interval=1,
            datatype=int,
            keep_last_value=False,
            aggregator=None,
            first_timestamp=None,
            last_timestamp=None
        ):
        """Initializes a sparse time series"""
        self.first_timestamp = first_timestamp
        self.last_timestamp = last_timestamp
        if isinstance(interval, int):
            self.interval = interval
        self.datatype = datatype
        self.keep_last_value = keep_last_value
        if aggregator is None:
            self.aggregator = lambda old, new: new
        else:
            self.aggregator = aggregator
        self._values = {}

    def __len__(self):
        """Returns the length of the time series"""
        if self.first_timestamp is None or self.last_timestamp is None:
            return 0
        return int(
            (self.last_timestamp - self.first_timestamp).total_seconds()
        ) // self.interval + 1

    def __getitem__(self, key):
        """Gets the value at interval [key]"""
        if not isinstance(key, datetime.datetime):
            raise TypeError("Keys must be of type datetime.datetime")
        base_key = self.floor_time(key)
        if base_key in self._values:
            return self._values[base_key]
        # if we /should/ know this, return the default constructor or the
        # last value in the sequence (if self.keep_last_value)
        if self.first_timestamp <= base_key <= self.last_timestamp:
            if self.keep_last_value:
                last_value = None
                for ts in self: # use our __iter__
                    # we already know base_key is not in self._values
                    if ts in self._values:
                        last_value = self._values[ts]
                    elif ts == base_key and last_value is not None:
                        return last_value
            # if we fall through to this point, default constructor
            return self.datatype()
        raise KeyError(key)

    def __setitem__(self, key, value):
        """Sets the value at interval [key]"""
        if not isinstance(key, datetime.datetime):
            raise TypeError("Keys must be of type datetime.datetime")
        if not isinstance(value, self.datatype):
            raise ValueError("Value {} is not of type {}".format(
                repr(value), repr(self.datatype)
            ))
        base_key = self.floor_time(key)
        # track first and last timestamps
        if self.first_timestamp is None:
            self.first_timestamp = base_key
        if self.last_timestamp is None:
            self.last_timestamp = base_key
        if base_key < self.first_timestamp:
            self.first_timestamp = base_key
        if base_key > self.last_timestamp:
            self.last_timestamp = base_key
        # resolve duplicates
        if base_key in self._values:
            self._values[base_key] = self.aggregator(
                self._values[base_key], value
            )
        else:
            self._values[base_key] = value

    def __iter__(self):
        """Iterates over keys in our time range"""
        if len(self) == 0:
            return
        current = self.first_timestamp
        delta = datetime.timedelta(0, self.interval)
        while current <= self.last_timestamp:
            yield current
            current += delta

    def __contains__(self, ts):
        """Tests whether ts is in this time interval"""
        if not isinstance(ts, datetime.datetime):
            return False
        base_key = self.floor_time(key)
        return self.first_timestamp <= base_key <= self.last_timestamp

    def __repr__(self):
        """Represents the interval"""
        repr_strings = [
            "{}: {}".format(repr(ts), repr(v)) for ts, v in self.items()
        ]
        all_reprs = ", ".join(repr_strings)
        return "{}({{{}}})".format(self.__class__.__name__, all_reprs)

    def floor_time(self, ts):
        """Returns the floor function for [ts] based on self.interval"""
        return datetime.datetime.fromtimestamp(
            int(ts.timestamp()) // self.interval * self.interval
        )

    def items(self):
        """Iterates over the time period, producing tuples of time series"""
        for ts in self:
            yield ts, self[ts]

    def keys(self):
        """Iterates over the time period, producing keys of time series"""
        for ts in self:
            yield ts

    def values(self):
        """Iterates over the time period, producing values of time series"""
        for ts in self:
            yield self[ts]

    def set_start(self, ts):
        """Sets the starting timestamp for the series.

        If the current starting timestamp is less than [ts], no effect.
        """
        base_key = self.floor_time(ts)
        if self.first_timestamp is None or base_key < self.first_timestamp:
            self.first_timestamp = base_key

    def set_end(self, ts):
        """Sets the ending timestamp for the series.

        If the current ending timestamp is greater than [ts], no effect.
        """
        base_key = self.floor_time(ts)
        if self.last_timestamp is None or base_key > self.last_timestamp:
            self.last_timestamp = base_key

    def sum(self):
        """Returns the sum of all values in the time series"""
        return sum(self._values.values())
