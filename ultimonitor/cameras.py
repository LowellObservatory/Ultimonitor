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

from requests import get as httpget
from requests.exceptions import ConnectionError as RCE


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
