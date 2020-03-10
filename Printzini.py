# -*- coding: utf-8 -*-
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#  Created on 17 Aug 2019
#
#  @author: rhamilton

"""The Great Printzini

Monitor for the Ultimaker series of 3D printers, using their supported API.
Also supports a Raspberry Pi camera to take additional pictures of the print.
"""

from __future__ import division, print_function, absolute_import

from ligmos import utils

from ultimonitor import confparser
from ultimonitor import leds, monitoring


def main(conffile):
    """
    """
    cDict = confparser.parseConf(conffile)

    # A quick way to disable stuff while debugging
    #   These need to be moved out to the config file
    #   (or, I just need to verify that the 'enable' keys work there)
    squashEmail = False
    squashPiCam = False
    squashUltiCam = False

    # These are our color options, given as a dict of color names and their
    #   associated HSV (!NOT RGB!) properties which are actually sent to the
    #   case LEDs via the printer API
    hsvCols = leds.pallettBobRoss()

    # The numerical codes are seen in "printer/diagnostics/temperature_flow/"
    #   See also: griffin/printer/drivers/marlin/applicationLayer.py
    #
    # When printing, 0 denotes hotend #1 and 1 denotes hotend #2. We
    #   can just simplify things and call both "printing" for now
    # TODO: Figure out if there are additional valid states in 2 thru 9
    flowStateMap = {0: 'printing',
                    1: 'printing',
                    10: 'idle',
                    11: 'pausing',
                    12: 'paused',
                    13: 'resuming',
                    14: 'pre_print',
                    15: 'post_print',
                    16: 'wait_cleanup',
                    17: 'wait_user_action'}

    # NOTE: There are 3 additional states (error, maintenance, booting) that
    #   aren't captured in the flowStateMap since they originate elsewhere
    #   in the Ultimaker griffin engine
    statusColors = {"idle": hsvCols["PrussianBlue"],
                    "printing": hsvCols["TitaniumWhite"],
                    "pausing": hsvCols["IndianYellow"],
                    "paused": hsvCols["CadmiumYellow"],
                    "resuming": hsvCols["IndianYellow"],
                    "pre_print": hsvCols["SapGreen"],
                    "post_print": hsvCols["BrightBlue"],
                    "wait_cleanup": hsvCols["BrightGreen"],
                    "wait_user_action": hsvCols["BrightRed"],
                    "error": hsvCols["BrightRed"],
                    "maintenance": hsvCols["CadmiumYellow"],
                    "booting": hsvCols["PhthaloGreen"]}

    # Start logging to a file
    utils.logs.setup_logging(logName="./logs/printzini.txt", nLogs=10)

    # Set up our signal
    runner = utils.common.HowtoStopNicely()

    # Actually monitor
    monitoring.monitorUltimaker(cDict, flowStateMap, statusColors, runner,
                                loopInterval=30,
                                squashEmail=squashEmail,
                                squashPiCam=squashPiCam,
                                squashUltiCam=squashUltiCam)

    print("Printzini has exited normally!  Enjoy the world of 3D.")


if __name__ == "__main__":
    conffile = './config/ultimonitor.conf'
    main(conffile)
