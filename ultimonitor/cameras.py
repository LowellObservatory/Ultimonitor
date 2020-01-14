# -*- coding: utf-8 -*-
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#  Created on 21 Aug 2019
#
#  @author: rhamilton

"""One line description of module.

Further description.
"""

from __future__ import division, print_function, absolute_import

from time import sleep
from fractions import Fraction
from datetime import datetime as dt

from requests import get as httpget
from requests.exceptions import ConnectionError as RCE

try:
    import picamera
    from picamera import PiCamera, Color
except ImportError:
    picamera = None


def grab_ultimaker(printerip):
    """
    NOTE: This returns the whole requests HTTP get object
    """
    imgloc = "http://%s:8080/?action=snapshot" % (printerip)

    # I don't care much about the filename since I operate on the actual
    #   image itself (in img.content), but it's nice to save
    outfile = "instasnap.jpg"
    print("Attempting to write image to %s" % (outfile))

    with open(outfile, "wb") as f:
        img = httpget(imgloc, timeout=5.)
        # Check the HTTP response;
        #   200 - 400 == True
        #   400 - 600 == False
        #   Other way to do it might be to check if img.status_code == 200
        if img.ok is True:
            print("Good grab!")
            f.write(img.content)
        else:
            # This will be caught elsewhere
            print("Bad grab :(")
            img = None
            raise RCE

    return img


def piCamInit(camSettings):
    if picamera is not None and camSettings is not None:
        picamera.PiCamera.CAPTURE_TIMEOUT = 60

        # https://picamera.readthedocs.io/en/latest/fov.html#camera-modes
        camera = PiCamera(sensor_mode=3)

        # Allow the camera to use a framerate that's high (1/10 per second)
        #   or fast (30 per second) depending on conditions. Best to do
        #   this first before anything else
        camera.framerate_range = (Fraction(1, 10), Fraction(30, 1))

        # Need to make sure these are integers since they're parsed in
        #   from a configuration file and are probably strings
        camera.resolution = (int(camSettings.resolution[0][1:]),
                             int(camSettings.resolution[1][:-1]))
        camera.vflip = camSettings.flipv
        camera.hflip = camSettings.fliph

        camera.drc_strength = camSettings.drc_strength
        camera.exposure_mode = camSettings.exposure_mode
        camera.meter_mode = camSettings.meter_mode
        # Same as resolution above - this needs to be an int!
        camera.exposure_compensation = int(camSettings.exposure_compensation)
        camera.image_denoise = camSettings.image_denoise

        print("Allowing camera to reticulate some splines...")
        sleep(15)

        # To fix exposure gains, let analog_gain and digital_gain settle on
        #   reasonable values, then set exposure_mode to 'off'.
        camera.exposure_mode = 'off'
    else:
        camera = None

    return camera


def piCamCapture(camSettings, debug=False):
    now = dt.utcnow()
    nowstr = now.strftime("%Y%m%d_%H%M%S")
    print("Starting capture at %s" % (nowstr))

    # Init the camera
    try:
        camera = piCamInit(camSettings)
    except picamera.exc.PiCameraMMALError:
        print("Camera is likely busy! Try again later.")

    if camera is not None:
        outname = "./%s.png" % (nowstr)

        # If camera.shutter_speed is 0, camera.exposure_speed will be the
        #   actual/used value determined during the above sleeps
        print("exp: %f, shut: %f" % (camera.shutter_speed,
                                     camera.exposure_speed))
        expspeed = round(camera.exposure_speed/1e6, 6)

        annotation = "Time: %s\nShutterSpeed: %s sec" % (nowstr, str(expspeed))

        # This has to happen *before* the capture!
        camera.annotate_background = Color("black")
        camera.annotate_text = annotation

        # Actually do the capture now!
        print("Starting capture...")
        camera.capture(outname)
        print("Capture complete!")

        if debug is True:
            print("Captured %s" % (outname))

        print("Took a %d microseconds exposure." % (camera.exposure_speed))

        # https://github.com/waveform80/picamera/issues/528
        camera.framerate = 1
        camera.close()
    else:
        outname = None

    return outname
