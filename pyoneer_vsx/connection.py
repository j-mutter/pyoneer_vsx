"""Module containing the connection wrapper for the AVR interface."""
import asyncio
import logging
from .receiver import Receiver

__all__ = ('Connection')
_LOGGER = logging.getLogger(__name__)

# In Python 3.4.4, `async` was renamed to `ensure_future`.
try:
    ensure_future = asyncio.ensure_future
except AttributeError:
    ensure_future = asyncio.async


class Connection:
    """Connection handler to maintain network connection for AVR Protocol."""

    def __init__(self):
        """Instantiate the Connection object."""
        _LOGGER = logging.getLogger(__name__)

    @classmethod
    @asyncio.coroutine
    def create(cls, host='localhost', port=23,
               auto_reconnect=True, loop=None,
               update_callback=None, input_list=None):
        """Initiate a connection to a specific device.
        Here is where we supply the host and port and callback callables we
        expect for this AVR class object.
        :param host:
            Hostname or IP address of the device
        :param port:
            TCP port number of the device
        :param auto_reconnect:
            Should the Connection try to automatically reconnect if needed?
        :param loop:
            asyncio.loop for async operation
        :param update_callback:
            This function is called whenever AVR state data changes
        :param input_list:
            The map of input numbers and names. Leave blank for defaults
        :type host:
            str
        :type port:
            int
        :type auto_reconnect:
            boolean
        :type loop:
            asyncio.loop
        :type update_callback:
            callable
        :type input_list:
            dictionary
        """
        assert port >= 0, 'Invalid port value: %r' % (port)
        conn = cls()

        conn.host = host
        conn.port = port
        conn._loop = loop or asyncio.get_event_loop()
        conn._retry_interval = 1
        conn._closed = False
        conn._closing = False
        conn._halted = False
        conn._auto_reconnect = auto_reconnect

        def connection_lost():
            """Function callback for Protocoal class when connection is lost."""
            if conn._auto_reconnect and not conn._closing:
                ensure_future(conn._reconnect(), loop=conn._loop)

        conn.receiver = Receiver(
            connection_lost_callback=connection_lost, loop=conn._loop,
            update_callback=update_callback, input_list=input_list)

        yield from conn._reconnect()

        return conn

    @property
    def transport(self):
        """Passthrough access to the underlying receiver transport.
        """
        return self.receiver.transport

    def _get_retry_interval(self):
        return self._retry_interval

    def _reset_retry_interval(self):
        self._retry_interval = 1

    def _increase_retry_interval(self):
        self._retry_interval = min(300, 1.5 * self._retry_interval)

    @asyncio.coroutine
    def _reconnect(self):
        while True:
            try:
                if self._halted:
                    yield from asyncio.sleep(2, loop=self._loop)
                else:
                    _LOGGER.info('Connecting to Pioneer AVR at %s:%d',
                                  self.host, self.port)
                    yield from self._loop.create_connection(
                        lambda: self.receiver, self.host, self.port)
                    self._reset_retry_interval()
                    return

            except OSError:
                self._increase_retry_interval()
                interval = self._get_retry_interval()
                _LOGGER.warning('Connecting failed, retrying in %i seconds',
                              interval)
                yield from asyncio.sleep(interval, loop=self._loop)

    def close(self):
        """Close the AVR device connection and don't try to reconnect."""
        _LOGGER.warning('Closing connection to AVR')
        self._closing = True
        if self.receiver.transport:
            self.receiver.transport.close()

    def halt(self):
        """Close the AVR device connection and wait for a resume() request."""
        _LOGGER.warning('Halting connection to AVR')
        self._halted = True
        if self.receiver.transport:
            self.receiver.transport.close()

    def resume(self):
        """Resume the AVR device connection if we have been halted."""
        _LOGGER.warning('Resuming connection to AVR')
        self._halted = False
