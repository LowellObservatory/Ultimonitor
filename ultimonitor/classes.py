# -*- coding: utf-8 -*-
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#  Created on 29 Aug 2019
#
#  @author: rhamilton

"""One line description of module.

Further description.
"""

from __future__ import division, print_function, absolute_import


class jobInProgress(object):
    def __init__(self):
        self.foundTime = None
        self.reportedTime = None
        self.printSetup = None
        self.notices = {"preamble": False,
                        "start": False,
                        "done10": False,
                        "done50": False,
                        "done90": False,
                        "completed": False}
        self.jobname = None
        self.uuid = None
        self.time_elapsed = None
        self.time_total = None
        self.progress = None


class threeDimensionalPrinter(object):
    def __init__(self):
        self.ip = None
        self.type = None
        self.apiid = None
        self.apikey = None
        self.enabled = True
