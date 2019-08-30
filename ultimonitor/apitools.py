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

import json
import requests
from requests.auth import HTTPDigestAuth


def setProperty(apiid, apikey, printerip, endpoint, vals, goodVal=204):
    """
    REQUIRES API information for authentication.

    With great power comes great responsibility.

    vals should be a dict, which gets turned into JSON before sending.
    """
    if printerip.startswith("http") is False:
        apiloc = "http://%s/api/v1/" % (printerip)
    else:
        apiloc = printerip

    queryendpoint = apiloc + endpoint

    # Set up the needed authentication
    # requests.post(apiloc + "auth/request", data={"application": })
    auth = HTTPDigestAuth(apiid, apikey)
    headers = {'Content-Type': 'application/json',
               'Accept': 'application/json'}

    jvals = json.dumps(vals)
    print("Sending %s to %s" % (jvals, queryendpoint))
    rp = requests.put(queryendpoint, headers=headers,
                      json=vals, auth=auth, timeout=5.)

    if rp.status_code != goodVal:
        print("PUT request to %s failed!" % (queryendpoint))
        print(rp)


def queryChecker(printerip, endpoint, goodStatus=200, debug=False):
    """
    """
    if printerip.startswith("http") is False:
        apiloc = "http://%s/api/v1/" % (printerip)
    else:
        apiloc = printerip

    queryendpoint = apiloc + endpoint

    try:
        req = requests.get(queryendpoint)
    except Exception as err:
        # TODO: Catch the right exception (socket.gaierror?)
        print(str(err))
        req = {}

    if req != {}:
        if debug is True:
            print(queryendpoint)
            print(req.status_code)
            print(req.content)
        if req.status_code == goodStatus:
            req = json.loads(req.content)
        else:
            req = {}

    return req
