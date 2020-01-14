# -*- coding: utf-8 -*-
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#  Created on 17 Aug 2019
#
#  @author: rhamilton

"""One line description of module.

Further description.
"""

from __future__ import division, print_function, absolute_import

import colorsys

from . import apitools as api


def pallettBobRoss():
    """
    I started from these:
    https://thomaspark.co/2015/11/bob-ross-color-palette-in-css/

    But I quickly realized that the Ultimaker's LED strips look like
    garbage/too dark for any brightness < 50, so I adjusted
    them all upwards to have a brightness of >= 70.
    """

    happyColors = {"SapGreen": "#22B338",
                   "AlizarinCrimson": "#B33000",
                   "VanDykeBrown": "#B38F6F",
                   "DarkSienna": "#B3573B",
                   "MidnightBlack": "#000000",
                   "PrussianBlue": "#054EB3",
                   "PhthaloBlue": "#2100B3",
                   "PhthaloGreen": "#308AB3",
                   "CadmiumYellow": "#FFEC00",
                   "YellowOchre": "#C79B00",
                   "IndianYellow": "#FFB800",
                   "BrightRed": "#B30000",
                   "BrightGreen": "#00B300",
                   "BrightBlue": "#0000B3",
                   "TitaniumWhite": "#FFFFFF"}

    hsvHappyColors = {}
    # Now convert them to HSV so I can send them to the printer's LED
    for color in happyColors:
        colHex = happyColors[color][1:]
        colRGB = [int(colHex[i:i+2], 16) for i in range(0, len(colHex), 2)]
        colHSV = colorsys.rgb_to_hsv(colRGB[0]/255.,
                                     colRGB[1]/255.,
                                     colRGB[2]/255.)

        # Should consider doing a quick gamma correction on these at some
        #   point in the future...but for now, just knock down the
        #   precision so we don't chase our tail due to rounding

        # A fudge factor to appease the GODO. >= 1 otherwise it'll brighten
        ledGODO = 2.5

        colHSV = {"hue": round(colHSV[0]*360., 5),
                  "saturation": round(colHSV[1]*100., 5),
                  "brightness": round(colHSV[2]*100./ledGODO, 5)}

        # print(color, colRGB, colHSV)
        hsvHappyColors.update({color: colHSV})

    return hsvHappyColors


def ledCheck(printerConfig, hsvColors, statusColors, statusStr):
    """
    """
    # Checking/setting status LED colors
    actualLED = api.queryChecker(printerConfig.ip, "printer/led")
    desiredLED = hsvColors[statusColors[statusStr]]

    ledChange = False
    # I can evantually just collapse this if I explicitly remove
    #   the 'blink' property in the actualLED dict
    for cprop in actualLED:
        # (I don't care about the blink property for now)
        if cprop != 'blink':
            if actualLED[cprop] != desiredLED[cprop]:
                print("%s mismatch!" % (cprop))
                print("Expected %s but it's currently %s" %
                      (desiredLED[cprop], actualLED[cprop]))
                ledChange = True
                # Bail early because we already know we have to change
                break

    if ledChange is True:
        api.setProperty(printerConfig.apiid,
                        printerConfig.apikey,
                        printerConfig.ip, "printer/led", desiredLED)
