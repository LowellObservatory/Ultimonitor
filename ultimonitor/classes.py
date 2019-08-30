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


class piCamSettings(object):
    def __init__(self):
        # Suitable for darker environments
        self.resolution = [864, 648]
        self.flipv = False
        self.fliph = False
        self.drc_strength = 'high'
        self.exposure_mode = 'night'
        self.meter_mode = 'matrix'
        self.exposure_compensation = 25
        self.image_denoise = False
