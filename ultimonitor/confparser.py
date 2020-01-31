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
    eConf = confparsers.checkEnabled(pConf)

    expectedSectionNames = ['printerSetup', 'email',
                            'picam',
                            'databaseSetup', 'databaseQuery']

    returnable = {}
    for section in expectedSectionNames:
        if section == 'printerSetup':
            clstype = classes.threeDimensionalPrinter
        elif section == 'email':
            clstype = classes.emailSNMP
        elif section == 'picam':
            clstype = classes.piCamSettings
        elif section == 'databaseSetup':
            clstype = ligmosclass.baseTarget
        else:
            clstype = None

        if clstype is not None:
            try:
                actualConfig = confUtils.assignConf(eConf[section], clstype)
                if section == 'email':
                    # Read in the footer file as a text string
                    try:
                        with open(pConf['email']['footer'], 'r') as f:
                            actualConfig.footer = f.read()
                    except (OSError, IOError):
                        actualConfig.footer = None

                validSect = {section: actualConfig}
            except KeyError:
                print("WARNING: MISSING EXPECTED CONFIGURATION SECTION!")
                print("%s NOT FOUND OR NOT ENABLED IN %s" % \
                      (section, confName))
                validSect = None

        returnable.update(validSect)

    return returnable
