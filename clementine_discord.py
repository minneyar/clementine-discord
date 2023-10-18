#!/usr/bin/env python3

# Clementine / Discord Integration by minneyar
# fork by kitten99

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

DETAILS_STRING = '{artist} - {title}'
ALBUM_STRING = '{album}'
CLIENT_ID = 1163635305933451264

class PresenceUpdater:
    def __init__(self):
        logging.basicConfig(stream=sys.stdout, level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing.")

        self.bus = dbus.SessionBus()
        self.client = pypresence.Presence(CLIENT_ID)
        self.player = None
        self.prop_iface = None
        self.large_image_key = "logo"
        self.large_image_text = "Clementine"
        self.small_image_key = "play"
        self.small_image_text = "Playing"

    def run(self):
        while True:
            try:
                if not self.prop_iface:
                    self.logger.info("Connecting to Clementine.")
                    self.player = self.bus.get_object('org.mpris.MediaPlayer2.clementine', '/org/mpris/MediaPlayer2')
                    self.prop_iface = dbus.Interface(self.player, dbus_interface='org.freedesktop.DBus.Properties')

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
                state = 'Stopped'
                small_image_key = "stopbut"
                small_image_text = "Stopped"
            elif playback_status == 'Paused':
                details = 'Paused'
                state = None
                small_image_key = "pausebut"
                small_image_text = "Paused"
            else:
                self.logger.debug("Clementine Metadata: %s" % metadata)
                artist = ', '.join([str(a) for a in metadata['xesam:artist']])
                title = str(metadata['xesam:title'])
                album = metadata['xesam:album']
                details = DETAILS_STRING.format(artist=artist, title=title)
                state = ALBUM_STRING.format(album=album)
                small_image_key = "playbut"
                small_image_text = "Playing"

            if playback_status == 'Playing':
                try:
                    length_s = metadata['mpris:length'] / 1000000
                    time_now = time.time()
                    time_start = time_now - position_s
                    time_end = time_start + length_s
                except KeyError:
                    # Some media types may not provide length information; just ignore it
                    pass
            self.logger.debug("Updating Discord.")
            self.client.update(
                state=state,
                details=details,
                start=time_start,
                end=time_end,
                large_image=self.large_image_key,
                large_text=self.large_image_text,
                small_image=small_image_key,
                small_text=small_image_text
            )
            time.sleep(15)

    def close(self):
        self.logger.info("Shutting down.")
        if hasattr(self, 'client'):
            self.client.close()

if __name__ == '__main__':
    updater = PresenceUpdater()
    try:
        updater.run()
    finally:
        updater.close()