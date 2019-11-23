#!/usr/bin/env python3
# Copyright 2019 minneyar
#
# Redistribution and use in source and binary forms, with or without modification, are permitted provided that the
# following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following
# disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the
# following disclaimer in the documentation and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its contributors may be used to endorse or promote
# products derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES,
# INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE
# USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import struct
import sys

import dbus
import logging
import time
import pypresence

# Any of the keys in Clementine's metadata are valid here, but note that colons
# will be replaced with dashes.
# To see a list of keys, play a song and run:
# qdbus org.mpris.MediaPlayer2.clementine /org/mpris/MediaPlayer2 org.freedesktop.DBus.Properties.Get \
#     org.mpris.MediaPlayer2.Player Metadata
DETAILS_STRING = '🎵 {xesam-title} ({xesam-album})'
CLIENT_ID = 647617680072900608


class PresenceUpdater:
    def __init__(self):
        logging.basicConfig(stream=sys.stdout, level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing.")

        self.bus = dbus.SessionBus()
        self.client = pypresence.Presence(CLIENT_ID)
        self.player = None
        self.prop_iface = None

    def run(self):
        while True:
            try:
                if not self.prop_iface:
                    self.logger.info("Connecting to Clementine.")
                    self.player = self.bus.get_object('org.mpris.MediaPlayer2.clementine',
                                                      '/org/mpris/MediaPlayer2')
                    self.prop_iface = dbus.Interface(self.player,
                                                     dbus_interface='org.freedesktop.DBus.Properties')

                self.logger.info("Connecting to Discord.")
                self.client.connect()

                self.update_loop()
            except dbus.exceptions.DBusException as e:
                self.logger.warning("Error communicating with Clementine: %s" % str(e))
                self.logger.warning("Reconnecting in 15s.")
                self.player = None
                self.prop_iface = None
                time.sleep(15)
            except (pypresence.exceptions.InvalidID, ConnectionRefusedError, struct.error) as e:
                self.logger.warning("Error communicating with Discord: %s" % str(e))
                self.logger.warning("Reconnecting in 15s.")
                time.sleep(15)

    def update_loop(self):
        while True:
            self.logger.debug("Reading data from Clementine.")
            try:
                metadata = self.prop_iface.Get('org.mpris.MediaPlayer2.Player', 'Metadata')
                position_s = self.prop_iface.Get('org.mpris.MediaPlayer2.Player', 'Position') / 1000000
                playback_status = self.prop_iface.Get('org.mpris.MediaPlayer2.Player', 'PlaybackStatus')
            except dbus.exceptions.DBusException as e:
                self.client.clear()
                raise e

            time_start = None
            time_end = None

            if playback_status == 'Stopped':
                details = None
            else:
                tmp_metadata = dict()
                for key, value in metadata.items():
                    tmp_metadata[key.replace(':', '-')] = value
                details = DETAILS_STRING.format(**tmp_metadata)

            if playback_status == 'Playing':
                length_s = metadata['mpris:length'] / 1000000
                time_now = time.time()
                time_start = time_now - position_s
                time_end = time_start + length_s
            self.logger.debug("Updating Discord.")
            self.client.update(state=playback_status,
                               details=details,
                               start=time_start,
                               end=time_end)
            time.sleep(15)

    def close(self):
        self.logger.info("Shutting down.")
        self.client.close()


if __name__ == '__main__':
    updater = PresenceUpdater()
    try:
        updater.run()
    finally:
        updater.close()
