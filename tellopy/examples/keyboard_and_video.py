"""
tellopy sample using keyboard and video player

Requires mplayer to record/save video.


Controls:
- tab to lift off
- WASD to move the drone
- space/shift to ascend/descent slowly
- Q/E to yaw slowly
- arrow keys to ascend, descend, or yaw quickly
- backspace to land, or P to palm-land
- R to start recording video, R again to stop recording
  (video will be saved to a timestamped file in ~/Pictures/)
- Z to toggle camera zoom state
  (zoomed-in widescreen or high FOV 4:3)
"""

import time
import sys
import tellopy
import pygame
import pygame.display
import pygame.key
import pygame.locals
import pygame.font
import os
import datetime
from subprocess import Popen, PIPE

prev_flight_data = None
video_player = None
video_recorder = None
font = None
wid = None

def toggle_recording(drone, speed):
    global video_recorder
    if speed == 0:
        return

    if video_recorder:
        # already recording, so stop
        video_recorder.stdin.close()
        status_print('Video saved to %s' % video_recorder.video_filename)
        video_recorder = None
        return

    # start a new recording
    filename = '%s/Pictures/tello-%s.mp4' % (os.getenv('HOME'), datetime.datetime.now().isoformat())
    video_recorder = Popen([
        'mencoder', '-', '-vc', 'x264', '-fps', '30', '-ovc', 'copy',
        '-of', 'lavf', '-lavfopts', 'format=mp4', '-ffourcc', 'avc1',
        # '-really-quiet',
        '-o', filename,
    ], stdin=PIPE)
    video_recorder.video_filename = filename
    status_print('Recording video to %s' % filename)
    video_file = open(filename, 'w')

def palm_land(drone, speed):
    if speed == 0:
        return
    drone.palm_land()

def toggle_zoom(drone, speed):
    if speed == 0:
        return
    drone.set_video_mode(not drone.zoom)

controls = {
    'w': 'forward',
    's': 'backward',
    'a': 'left',
    'd': 'right',
    'space': 'up',
    'left shift': 'down',
    'right shift': 'down',
    'q': 'counter_clockwise',
    'e': 'clockwise',
    # arrow keys for fast turns and altitude adjustments
    'left': lambda drone, speed: drone.counter_clockwise(speed*2),
    'right': lambda drone, speed: drone.clockwise(speed*2),
    'up': lambda drone, speed: drone.up(speed*2),
    'down': lambda drone, speed: drone.down(speed*2),
    'tab': lambda drone, speed: drone.takeoff(),
    'backspace': lambda drone, speed: drone.land(),
    'p': palm_land,
    'r': toggle_recording,
    'z': toggle_zoom,
    # not implemented yet
    #'enter': lambda drone: drone.photo()
}

def status_print(text):
    if video_recorder:
        text = text + ' [REC]'
    pygame.display.set_caption(text)
    print(text)

def handler(event, sender, data, **args):
    global prev_flight_data
    global video_player
    global video_recorder
    drone = sender
    if event is drone.EVENT_FLIGHT_DATA:
        text = str(data)
        if data.battery_percentage <= 10:
            text = '!! LOW BAT !!' + text
        if prev_flight_data != text:
            status_print(text)
            prev_flight_data = text
    elif event is drone.EVENT_VIDEO_FRAME:
        if video_player is None:
            video_player = Popen([
                'mplayer', '-fps', '30', '-really-quiet', '-wid', str(wid),
                '-'],
                stdin=PIPE)
        try:
            video_player.stdin.write(data)
            if video_recorder:
                video_recorder.stdin.write(data)
        except IOError as err:
            status_print(str(err))
            video_player = None
    else:
        status_print('event="%s" data=%s' % (event.getname(), str(data)))


def update(old, new, max_delta=0.3):
    if abs(old - new) <= max_delta:
        res = new
    else:
        res = 0.0
    return res


def main():
    pygame.init()
    pygame.display.init()
    pygame.display.set_mode((1280, 720))
    pygame.font.init()

    global font
    font = pygame.font.Font(None, 32)

    global wid
    wid = pygame.display.get_wm_info()['window']
    print wid

    drone = tellopy.Tello()
    drone.connect()
    drone.start_video()
    drone.subscribe(drone.EVENT_FLIGHT_DATA, handler)
    drone.subscribe(drone.EVENT_VIDEO_FRAME, handler)
    speed = 30
    throttle = 0.0
    yaw = 0.0
    pitch = 0.0
    roll = 0.0

    try:
        while 1:
            time.sleep(0.01)  # loop with pygame.event.get() is too mush tight w/o some sleep
            for e in pygame.event.get():
                # WASD for movement
                if e.type == pygame.locals.KEYDOWN:
                    print '+',pygame.key.name(e.key)
                    keyname = pygame.key.name(e.key)
                    if keyname == 'escape':
                        drone.quit()
                        exit(0)
                    if keyname in controls:
                        key_handler = controls[keyname]
                        if type(key_handler) == str:
                            getattr(drone, key_handler)(speed)
                        else:
                            key_handler(drone, speed)

                elif e.type == pygame.locals.KEYUP:
                    print '-',pygame.key.name(e.key)
                    keyname = pygame.key.name(e.key)
                    if keyname in controls:
                        key_handler = controls[keyname]
                        if type(key_handler) == str:
                            getattr(drone, key_handler)(0)
                        else:
                            key_handler(drone, 0)
    except e:
        print str(e)
    finally:
        print 'Shutting down connection to drone...'
        if video_recorder:
            toggle_recording(drone, 1)
        drone.quit()
        exit(1)

if __name__ == '__main__':
    main()
