#!/usr/bin/env python3

import argparse
import asyncio
import pyoneer_vsx
import logging

log = logging.getLogger(__name__)

@asyncio.coroutine
def test():
    parser = argparse.ArgumentParser(description=test.__doc__)
    parser.add_argument('--host', default='127.0.0.1', help='IP or FQDN of AVR')
    parser.add_argument('--port', default='8102', help='Port of AVR')
    parser.add_argument('--verbose', '-v', action='count')

    args = parser.parse_args()

    if args.verbose:
        level = logging.DEBUG
    else:
        level = logging.ERROR

    logging.basicConfig(level=level)

    def log_callback(message):
        log.info('Callback invoked: %s' % message)

    host = args.host
    port = int(args.port)

    log.info('Connecting to Pioneer AVR at %s:%i' % (host, port))

    conn = yield from pyoneer_vsx.Connection.create(host=host,port=port,loop=loop,update_callback=log_callback)

    yield from asyncio.sleep(2, loop=loop)

    log.info('Power state is '+str(conn.receiver.power))
    conn.receiver.power = True

    yield from asyncio.sleep(2, loop=loop)
    log.info('Power state is '+str(conn.receiver.power))

    yield from asyncio.sleep(2, loop=loop)

    log.info('Setting input by name to CD')
    conn.receiver.input_name = 'CD'
 
    yield from asyncio.sleep(2, loop=loop)

    log.info('Setting input by number to BD(25)')
    conn.receiver.input_number = 25

    yield from asyncio.sleep(2, loop=loop)

    log.info('Setting volume to 50%')
    conn.receiver.volume_as_percentage = 0.5

    yield from asyncio.sleep(2, loop=loop)
    log.info('Volume is now ' + str(conn.receiver.volume))

    log.info('Setting volume to 25')
    conn.receiver.volume = 25

    yield from asyncio.sleep(2, loop=loop)
    log.info('Volume is now ' + str(conn.receiver.volume))

    conn.receiver.power = False
    yield from asyncio.sleep(2, loop=loop)
    log.info('Power state is '+str(conn.receiver.power))

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    loop = asyncio.get_event_loop()
    asyncio.async(test())
    loop.run_forever()