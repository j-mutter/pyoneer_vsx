# pyoneer_vsx
This is a Python package for interfacing with Pioneer receivers, primarily the VSX series, via telnet commands as outlined in [this specification](https://www.pioneerelectronics.com/StaticFiles/PUSA/Files/Home%20Custom%20Install/VSX-1120-K-RS232.PDF). 

This package was primarily created for use with [Home Assistant](https://www.home-assistant.io) to support receivers that do not work with the current implementation, as well as to extract all of the Pioneer-specific code out of Home Assistant, and to swtich to using a persistent connection via `asyncio`.

This package is based on [`python-anthemav`](https://github.com/nugget/python-anthemav) which provides similar functionality for Anthem receivers.

### Supported functionality

Currently this supports:
 - Power: on/off
 - Volume: 0-100%
 - Mute: on/off
 - Input selection

 The spec outlines more functionality, including listening modes, tone control, multi-zone power/input selection, etc, however for my purposes all I needed were the basics above.

### Update events

Because we keep a persistent connection to the receiver, we receive events every time a change is made to the receiver, either via a command we sent, or by a person physically interacting with the controls on the device itself.

For this reason we only, and always, update our internal state when we get these events, not when we initially send a command to the receiver.

## Setup

### Package installation

You can either install the package using `pip`:
```
pip3 install pyoneer-vsx
```

or clone the repo and install/run it from the source.

### Receiver

Connect your receiver to your network and ensure it has a static IP address either via the `System Setup > Network Setup` menu on the receiver itself, or by assigning it a fixed address on your router.

Also make sure you enable the `Network Standby` feature (also found in the `Network Setup` menu) so we can still connect to the receiver even when it is powered off.

## Testing

I have exclusively tested this with a VSX-822 and a VSX-1121, but any other Pioneer VSX series receiver (and possibly others) should work.

If download the code you can run the following command, substituting in the IP and port as needed:
```
python3 test_harness.py --host IP_ADDRESS --port PORT
```

This will attempt to connect to the receiver, turn it on, select a few different inputs, then turn it off, all with very verbose logging. At the end, your receiver should be off and when you turn it back on it should be set to the Blu-ray/BD input.

## Caveats

Due to the persistent connection described above, using this package will prevent any other applications/services, such as iOS or Android control apps, from connecting to the receiver. 