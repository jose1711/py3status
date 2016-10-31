# -*- coding: utf-8 -*-
"""
Display the current network transfer rate.

Configuration parameters:
    all_interfaces: ignore self.interfaces, but not self.interfaces_blacklist
        (default True)
    cache_timeout: how often we refresh this module in seconds
        (default 2)
    devfile: location of dev file under /proc
        (default '/proc/net/dev')
    format: format of the module output
        (default '{interface}: {total}')
    format_no_connection: when there is no data transmitted from the start of the plugin
        (default '')
    format_value: format to use for values
        (default "[\?min_length=11 {value:.1f} {unit}]")
    hide_if_zero: hide indicator if rate == 0
        (default False)
    interfaces: comma separated list of interfaces to track
        (default [])
    interfaces_blacklist: comma separated list of interfaces to ignore
        (default 'lo')
    si_units: use SI units
        (default False)
    thresholds: thresholds to use for colors
        (default [(0, 'bad'), (1024, 'degraded'), (1024*1024, 'good')])
    unit: unit to use. If the unit contains a multiplier prefix, only this
        exact unit will ever be used
        (default "B/s")

Format placeholders:
    {down} download rate
    {interface} name of interface
    {total} total rate
    {up} upload rate

Value placeholders:
    {unit} current unit
    {value} numeric value

Color thresholds:
    {down} Change color based on the value of down
    {total} Change color based on the value of total
    {up} Change color based on the value of up

Obsolete configuration parameters:
    precision: amount of numbers after dot (will be ignored if format_value is set)
        (default 1)

@author shadowprince
@license Eclipse Public License
"""

from __future__ import division  # python2 compatibility
from time import time


class Py3status:
    """
    """
    # available configuration parameters
    all_interfaces = True
    cache_timeout = 2
    devfile = '/proc/net/dev'
    format = "{interface}: {total}"
    format_no_connection = ''
    format_value = None
    hide_if_zero = False
    interfaces = []
    interfaces_blacklist = 'lo'
    si_units = False
    thresholds = [(0, "bad"), (1024, "degraded"), (1024*1024, "good")]
    unit = "B/s"
    # obsolete configuration parameters
    precision = None

    def __init__(self, *args, **kwargs):
        self.last_interface = None
        self.last_stat = self._get_stat()
        self.last_time = time()

    def post_config_hook(self):
        # parse some configuration parameters
        if not isinstance(self.interfaces, list):
            self.interfaces = self.interfaces.split(',')
        if not isinstance(self.interfaces_blacklist, list):
            self.interfaces_blacklist = self.interfaces_blacklist.split(',')

        if self.format_value is None:
            if self.precision is not None:
                if self.precision > 0:
                    self.left_align = 3 + 1 + self.precision + 1 + 5
                else:
                    self.left_align = 3 + 1 + 5
                self.format_value = "[\?min_length=%s {value:.%sf} {unit}]" % (self.left_align,
                                                                               self.precision)
            else:
                self.format_value = "[\?min_length=11 {value:.1f} {unit}]"
        elif self.precision is not None:
            self.py3.notify_user('net_rate.py: Both format_value and precision are set.'
                                 ' precision will be ignored')

    def currentSpeed(self):
        ns = self._get_stat()
        deltas = {}
        try:
            # time from previous check
            timedelta = time() - self.last_time

            # calculate deltas for all interfaces
            for old, new in zip(self.last_stat, ns):
                down = int(new[1]) - int(old[1])
                up = int(new[9]) - int(old[9])

                down /= timedelta
                up /= timedelta

                deltas[new[0]] = {'total': up+down, 'up': up, 'down': down, }

            # update last_ info
            self.last_stat = self._get_stat()
            self.last_time = time()

            # get the interface with max rate
            interface = max(deltas, key=lambda x: deltas[x]['total'])

            # if there is no rate - show last active interface, or hide
            if deltas[interface]['total'] == 0:
                interface = self.last_interface
                hide = self.hide_if_zero
            # if there is - update last_interface
            else:
                self.last_interface = interface
                hide = False

            # get the deltas into variable
            delta = deltas[interface] if interface else None

        except TypeError:
            delta = None
            interface = None
            hide = self.hide_if_zero

        response = {'cached_until': self.py3.time_in(self.cache_timeout)}

        if hide:
            response['full_text'] = ""
        elif not interface:
            response['full_text'] = self.format_no_connection
        else:
            self.py3.threshold_get_color(delta['down'], 'down')
            self.py3.threshold_get_color(delta['total'], 'total')
            self.py3.threshold_get_color(delta['up'], 'up')
            response['full_text'] = self.py3.safe_format(self.format, {
                'down': self._format_value(delta['down']),
                'total': self._format_value(delta['total']),
                'up': self._format_value(delta['up']),
                'interface': interface[:-1],
                })

        return response

    def _get_stat(self):
        """
        Get statistics from devfile in list of lists of words
        """
        def dev_filter(x):
            # get first word and remove trailing interface number
            x = x.strip().split(" ")[0][:-1]

            if x in self.interfaces_blacklist:
                return False

            if self.all_interfaces:
                return True

            if x in self.interfaces:
                return True

            return False

        # read devfile, skip two header files
        x = filter(dev_filter, open(self.devfile).readlines()[2:])

        try:
            # split info into words, filter empty ones
            return [list(filter(lambda x: x, _x.split(" "))) for _x in x]

        except StopIteration:
            return None

    def _format_value(self, value):
        """
        Return formatted string
        """
        value, unit = self.py3.format_units(value, unit=self.unit, si=self.si_units)
        return self.py3.safe_format(self.format_value, {'value': value, 'unit': unit})

if __name__ == "__main__":
    """
    Run module in test mode.
    """
    from py3status.module_test import module_test
    module_test(Py3status)
