"""Module to maintain AVR state information and network interface."""
import asyncio
import logging
import re
import time

from math import ceil

__all__ = ('AVR')
_LOGGER = logging.getLogger(__name__)

# In Python 3.4.4, `async` was renamed to `ensure_future`.
try:
    ensure_future = asyncio.ensure_future
except AttributeError:
    ensure_future = asyncio.async

COMMANDS = {
    'power_on': 'PO',
    'power_off': 'PF',
    'power_toggle': 'PZ',
    'volume_up': 'VU',
    'volume_down': 'VD',
    'volume_set': '{data:.3}VL',
    'mute_on': 'MO',
    'mute_off': 'MF',
    'mute_toggle': 'MZ',
    'input_select': '{data:.2}FN',
    'input_cycle_up': 'FU',
    'input_cycle_down': 'FD',
}

QUERIES = {
    'power': 'P',
    'volume': 'V',
    'mute': 'M',
    'input': 'F',
}

RESPONSE_FORMATS = {
    'power': 'PWR(?P<data>\d)',
    'volume': 'VOL(?P<data>\d{3})',
    'mute': 'MUT(?P<data>\d)',
    'input': 'FN(?P<data>\d{2})',
    'keepalive': 'R',
}

DEFAULT_INPUTS = {
    '00': 'PHONO',
    '01': 'CD',
    '02': 'TUNER',
    '03': 'CD-R/TAPE',
    '04': 'DVD',
    '05': 'TV/SAT',
    '10': 'VIDEO 1(VIDEO)',
    '12': 'MULTI CH IN',
    '14': 'VIDEO 2',
    '15': 'DVR/BDR',
    '17': 'iPod/USB',
    '19': 'HDMI 1',
    '20': 'HDMI 2',
    '21': 'HDMI 3',
    '22': 'HDMI 4',
    '23': 'HDMI 5',
    '24': 'HDMI 6',
    '25': 'BD',
    '26': 'HOME MEDIA GALLERY(Internet Radio)',
    '27': 'SIRIUS',
    '31': 'HDMI (cyclic)',
    '33': 'ADAPTER PORT',
}

class Receiver(asyncio.Protocol):
    """The Pioneer AVR IP control protocol handler."""

    def __init__(self, update_callback=None, loop=None, connection_lost_callback=None, input_list=None):
        """Protocol handler that handles all status and changes on AVR.
        This class is expected to be wrapped inside a Connection class object
        which will maintain the socket and handle auto-reconnects.
            :param update_callback:
                called if any state information changes in device (optional)
            :param connection_lost_callback:
                called when connection is lost to device (optional)
            :param loop:
                asyncio event loop (optional)
            :param input_list:
                lists of input numbers and names (optional)
            :type update_callback:
                callable
            :type: connection_lost_callback:
                callable
            :type loop:
                asyncio.loop
        """
        self._loop = loop
        self._connection_lost_callback = connection_lost_callback
        self._update_callback = update_callback
        self._input_list = input_list or DEFAULT_INPUTS
        self.transport = None

        for key in QUERIES:
            setattr(self, '_'+key, '')

        self._power = '0'

    def refresh(self):
        """Query device for all attributes that are known.
        This will force a refresh for all device queries that the module is
        aware of.  In theory, this will completely populate the internal state
        table for all attributes.
        This does not return any data, it just issues the queries.
        """
        _LOGGER.info('refresh_all')
        for key in QUERIES:
            self.query(key)

    #
    # asyncio network functions
    #

    def connection_made(self, transport):
        """Called when asyncio.Protocol establishes the network connection."""
        _LOGGER.info('Connection established to AVR')
        self.transport = transport

        limit_low, limit_high = self.transport.get_write_buffer_limits()
        _LOGGER.debug('Write buffer limits %d to %d', limit_low, limit_high)

        self.refresh()

    def data_received(self, data):
        """asyncio callback for any data recieved from the receiver."""
        if data != '':
            try:
                fullData = data.decode('ascii').strip()
                result = ''
                _LOGGER.debug(str.format('RX < {0}', fullData))
                lines = str.split(fullData, '\r\n')
            except:
                _LOGGER.error('Received invalid message. Skipping.')
                return

            for line in lines:
                parsed = self._parse_response(line)
                if parsed['attribute'] != 'keepalive':
                    _LOGGER.debug('Setting %s to %s', parsed['attribute'], parsed['data'])
                    setattr(self, '_'+parsed['attribute'], parsed['data'])
                    if self._update_callback:
                        self._loop.call_soon(self._update_callback, parsed['attribute'])

    def _parse_response(self, response_line):
        """Parse the raw response from the receiver"""
        _LOGGER.debug(str.format('Parsing response line: {0}', response_line))
        result = {}
        for attribute, format in RESPONSE_FORMATS.items():
            match = re.search(format, response_line)
            if match:
                _LOGGER.debug(str.format('Match found for {0}', attribute))
                result['attribute'] = attribute
                if match.groups():
                    result['data'] = match.group('data')
                else:
                    result['data'] = None
                break

        return result

    def connection_lost(self, exc):
        """Called when asyncio.Protocol loses the network connection."""
        if exc is None:
            _LOGGER.warning('eof from receiver?')
        else:
            _LOGGER.warning('Lost connection to receiver: %s', exc)

        self.transport = None

        if self._connection_lost_callback:
            self._loop.call_soon(self._connection_lost_callback)

    def query(self, prop):
        """Issue a query to the device for the given property.
        This function is used to request that the device supply the current
        state for a data item as described in the Pioneer API.
        This function does not return the result, it merely issues the request
        after which the response will be parsed via the normal callback
            :param prop: Any of the queriable properties
            :type prop: str
        :Example:
        >>> query('volume')
        """
        
        try:
            query_string = '?'+QUERIES[prop]
            self.send_data(query_string)
        except KeyError:
            _LOGGER.warning('Tried to query invalid property: %s', prop)

    def send_data(self, data):
        """Encode and send the given data to the device.
        Before sending the actual command or query we need to send a single
        carriage return and wait 100ms in order to wake up the main CPU from standby
            :param command: Any command as documented in the Pioneer API
            :type command: str
        :Example:
        >>> send_data('50VL')
        """
        encoded = (data+"\r").encode('ASCII')
        _LOGGER.debug('> %s', encoded)
        try:
            self.transport.write(b"\r")
            time.sleep(0.1)
            self.transport.write(encoded)
            time.sleep(0.01)
        except:
            _LOGGER.warning('Unable to send data')

    def send_command(self, command, data=None):
        command_data = COMMANDS[command]
        if data:
            command_data = command_data.format(data=data)

        self.send_data(command_data)

    #
    # Volume handlers.  Pioneer AVRs track volume internally as integers with a range
    # of 0 to 185, with 0 being silent, 1 being -80dB, and each subsequent
    # value being a 0.5dB step up, to a maximum of +12dB 
    #
    # We store the raw 0-185 value internally, but expose it in other formats for consumers
    #
    #   - volume (0-100)
    #   - volume_as_percentage (0-1 floating point)
    #

    def raw_volume_to_volume_percent(self, value):
        """Convert the raw Pioneer AVR volume value to a 0-1 float"""
        try:
            return (int(value) / 185)
        except ValueError:
            return 0

    def volume_percent_to_raw_volume(self, value):
        """Convert a 0-1 float volume to the 0-185 scale used by the Pioneer AVR"""
        try:
            return round(value * 185)
        except ValueError:
            return 0

    @property
    def raw_volume(self):
        """Current volume in 0.5 dB steps as per the Pioneer AVR spec (read/write).
        You can get or set the current value on the device with this property.
        Valid range from 0-185
        """
        try:
            return int(self._volume)
        except ValueError:
            return 0
        except NameError:
            return 0

    @raw_volume.setter
    def raw_volume(self, value):
        if isinstance(value, int) and 0 <= value <= 185:
            _LOGGER.debug('Setting raw_volume to '+str(value))
            # It turns out that not all receivers support the `volume_set` command
            # so we have to step up/down as needed until we hit our target.
            #
            # self.send_command('volume_set', str(value))
            self._step_to_target_volume(value)

    @property
    def volume(self):
        """Current volume level (read/write).
        You can get or set the current volume value on the device with this
        property.  Valid range from 0 to 100.
        :Examples:
        >>> volvalue = volume
        >>> volume = 20
        """
        try:
            return round(self.volume_as_percentage * 100)
        except ValueError:
            return 0

    @volume.setter
    def volume(self, value):
        if isinstance(value, int) and 0 <= value <= 100:
            self.raw_volume = self.volume_percent_to_raw_volume(value / 100)

    @property
    def volume_as_percentage(self):
        """Current volume as percentage (read/write).
        You can get or set the current volume value as a percentage.  Valid
        range from 0 to 1 (float).
        :Examples:
        >>> volper = volume_as_percentage
        >>> volume_as_percentage = 0.20
        """
        return self.raw_volume_to_volume_percent(self.raw_volume)

    @volume_as_percentage.setter
    def volume_as_percentage(self, value):
        if isinstance(value, float) or isinstance(value, int):
            if 0 <= value <= 1:
                value = self.volume_percent_to_raw_volume(value)
                self.raw_volume = value

    def volume_up(self):
        self.send_command('volume_up')

    def volume_down(self):
        self.send_command('volume_down')

    def _step_to_target_volume(self, target):
        # The volume up/down commands step in increments of odd numbers only, resulting in a 1db increase/decrease with each step
        actual_target = target + 1 if target % 2 == 0 else target
        # it also skips 001, so treat that as 0
        actual_target = 0 if actual_target < 3 else actual_target

        steps = ceil(abs(actual_target - self.raw_volume) / 2)

        for _ in range(steps):
            if actual_target > self.raw_volume:
                self.volume_up()
            else:
                self.volume_down()

    @property
    def power(self):
        """Report if device powered on or off (read/write).
        Returns and expects a boolean value.
        """
        if (self._power == "1") or (self._power == "2"):
            return False
        else:
            return True

    @power.setter
    def power(self, value):
        self._set_on_off('power', value)

    @property
    def mute(self):
        """Mute on or off (read/write)."""
        if (self._mute == "1"):
            return False
        else:
            return True

    @mute.setter
    def mute(self, value):
        self._set_on_off('mute', value)

    #
    # Inputs
    #

    @property
    def input_list(self):
        """List of all the configured inputs"""
        return list(self._input_list.values())

    @property
    def input_name(self):
        """Name of currently active input (read-write)."""
        return self._input_list.get(self._input, "Unknown")

    @input_name.setter
    def input_name(self, value):
        for key, name in self._input_list.items():
            if name == value:
                self._set_input(key)

    @property
    def input_number(self):
        """Number of currently active input (read-write)."""
        return self._input

    @input_number.setter
    def input_number(self, number):
        key = str(number).zfill(2)
        name = self._input_list[key]
        if name:
            self._set_input(key)

    #
    #  Helpers
    #

    def _set_on_off(self, key, value):
        if value is True:
            self.send_command(key+'_on')
        else:
            self.send_command(key+'_off')

    def _set_input(self, key):
        _LOGGER.debug('Setting input to %s', key)
        self.send_command('input_select', key)
