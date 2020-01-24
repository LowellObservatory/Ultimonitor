# -*- coding: utf-8 -*-
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#  Created on 14 Jan 2020
#
#  @author: rhamilton

"""One line description of module.

Further description.
"""

from __future__ import division, print_function, absolute_import

from ligmos.workers import confUtils
from ligmos.utils import confparsers
from ligmos.utils import classes as ligmosclass

from . import classes


def parseConf(confName):
    """
    Might eventually find a way to make this more generic and just
    use the master parser over in ligmos, but it's fine for now.
    """
    pConf = confparsers.rawParser(confName)

    # Assignments to the class parameters
    um3e = confUtils.assignConf(pConf['printerSetup'],
                                classes.threeDimensionalPrinter)
    email = confUtils.assignConf(pConf['email'],
                                 classes.emailSNMP)
    picamera = confUtils.assignConf(pConf['picam'],
                                    classes.piCamSettings)

    db = confUtils.assignConf(pConf['database'],
                              ligmosclass.baseTarget)


    # Read in the footer file as a text string
    try:
        with open(pConf['email']['footer'], 'r') as f:
            email.footer = f.read()
    except (OSError, IOError):
        email.footer = None

    return {"printer": um3e,
            "email": email,
            "database": db,
            "rpicamera": picamera}
