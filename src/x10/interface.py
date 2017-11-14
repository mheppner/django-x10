"""X10 interface for sending commands through PySerial.

Modified for PEP8 and Python 3 compatibility. Original text:
    X10 Firecracker CM17A Interface.

    -----------------------------------------------------------
    Copyright (c) 2010-2013 Collin J. Delker
    All rights reserved.

    Redistribution and use in source and binary forms, with or without
    modification, are permitted provided that the following conditions are met:

    1. Redistributions of source code must retain the above copyright notice, this
       list of conditions and the following disclaimer.
    2. Redistributions in binary form must reproduce the above copyright notice,
       this list of conditions and the following disclaimer in the documentation
       and/or other materials provided with the distribution.

    THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
    ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
    WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
    DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
    ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
    (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
    LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
    ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
    (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
    SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.#
    -----------------------------------------------------------

    NOTES:
      This software requires the pySerial python module:
      http://pyserial.sourceforge.net/

      Commands can be sent from the command line or from
      python scripts by calling send_command().

      X10 Firecracker CM17A protocol specificaiton:
      ftp://ftp.x10.com/pub/manuals/cm17a_protocol.txt

"""
import time

import serial


# Firecracker spec requires at least 0.5ms between bits
DELAY_BIT = 0.001  # Seconds between bits
DELAY_INIT = 0.15  # Powerup delay (default of 0.5)
DELAY_FIN = 0.5    # Seconds to wait before disabling after transmit (default of 1.0)

# House and unit code table
HOUSE_LIST = [
    0x6000,  # a
    0x7000,  # b
    0x4000,  # c
    0x5000,  # d
    0x8000,  # e
    0x9000,  # f
    0xA000,  # g
    0xB000,  # h
    0xE000,  # i
    0xF000,  # j
    0xC000,  # k
    0xD000,  # l
    0x0000,  # m
    0x1000,  # n
    0x2000,  # o
    0x3000   # p
]

UNIT_LIST = [
    0x0000,  # 1
    0x0010,  # 2
    0x0008,  # 3
    0x0018,  # 4
    0x0040,  # 5
    0x0050,  # 6
    0x0048,  # 7
    0x0058,  # 8
    0x0400,  # 9
    0x0410,  # 10
    0x0408,  # 11
    0x0400,  # 12
    0x0440,  # 13
    0x0450,  # 14
    0x0448,  # 15
    0x0458   # 16
]
MAX_UNIT = 16

# Command Code Masks
CMD_ON = 0x0000
CMD_OFF = 0x0020
CMD_BRT = 0x0088
CMD_DIM = 0x0098
CMD_ALL_ON = 0x0091
CMD_ALL_OFF = 0x0080
CMD_LAMPS_ON = 0x0094
CMD_LAMPS_OFF = 0x0084

# Data header and footer
DATA_HDR = 0xD5AA
DATA_FTR = 0xAD

# Raspberry Pi GPIO pins. Change to whatever you want to use.
DTR_PIN = 24
RTS_PIN = 25


class FirecrackerException(Exception):
    """Represents any exception with calling the firecracker."""

    pass


def set_standby(s):
    """Put Firecracker in standby."""
    s.setDTR(True)
    s.setRTS(True)


def set_off(s):
    """Turn firecracker 'off'."""
    s.setDTR(False)
    s.setRTS(False)


def send_data(s, data, bytes):
    """Send data to firecracker."""
    mask = 1 << (bytes - 1)

    for i in range(bytes):
        bit = data & mask
        if bit == mask:
            s.setDTR(False)
        elif bit == 0:
            s.setRTS(False)

        time.sleep(DELAY_BIT)
        set_standby(s)
        # Then stay in standby at least 0.5ms before next bit
        time.sleep(DELAY_BIT)
        # Move to next bit in sequence
        data = data << 1


def build_command(house, unit, action):
    """Generate the command word."""
    cmd = 0x00000000
    house_int = ord(house.upper()) - ord('A')

    # Add in the house code
    if house_int >= 0 and house_int <= ord('P') - ord('A'):
        cmd = cmd | HOUSE_LIST[house_int]
    else:
        raise FirecrackerException(f'Invalid house code: {house} {house_int}')

    # Add in the unit code. Ignore if bright or dim command,
    # which just applies to last unit.
    if str(unit).upper() == 'ALL' or str(unit).upper() == 'LAMPS':
        action = unit + '_' + action
    else:
        unit = int(unit)

        if unit > 0 and unit < MAX_UNIT:
            if action.upper() != 'BRT' and action.upper() != 'DIM':
                cmd = cmd | UNIT_LIST[unit - 1]
        else:
            raise FirecrackerException(f'Invalid unit code: {unit}')

    # Add the action code
    if action.upper() == 'ON':
        cmd = cmd | CMD_ON
    elif action.upper() == 'OFF':
        cmd = cmd | CMD_OFF
    elif action.upper() == 'BRT':
        cmd = cmd | CMD_BRT
    elif action.upper() == 'DIM':
        cmd = cmd | CMD_DIM
    elif action.upper() == 'ALL_ON':
        cmd = cmd | CMD_ALL_ON
    elif action.upper() == 'ALL_OFF':
        cmd = cmd | CMD_ALL_OFF
    elif action.upper() == 'LAMPS_ON':
        cmd = cmd | CMD_LAMPS_ON
    elif action.upper() == 'LAMPS_OFF':
        cmd = cmd | CMD_LAMPS_OFF
    else:
        raise FirecrackerException(f'Invalid action code: {action}')

    return cmd


def send_command(portname, house, unit, action):
    """Send Command to Firecracker.

    :param portname: Serial port to send to
    :param house: house code, character 'a' to 'p'
    :param unit: unit code, integer 1 to 16
    :param action: string 'ON', 'OFF', 'BRT' or 'DIM'
    """
    cmd = build_command(house, unit, action)
    if cmd is not None:
        try:
            s = serial.Serial(portname)
        except serial.SerialException:
            raise FirecrackerException(f'Error opening serial port: {portname}')

        # Initialize the firecracker
        set_standby(s)
        # Make sure it powers up
        time.sleep(DELAY_INIT)
        # Send data header
        send_data(s, DATA_HDR, 16)
        # Send data
        send_data(s, cmd, 16)
        # Send footer
        send_data(s, DATA_FTR, 8)
        # Wait for firecracker to finish transmitting
        time.sleep(DELAY_FIN)
        # Shut off the firecracker
        set_off(s)
        s.close()
