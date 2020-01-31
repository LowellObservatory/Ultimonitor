# -*- coding: utf-8 -*-
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#  Created on 23 Jan 2020
#
#  @author: rhamilton

"""Rudolf Julius Emanuel Clausius

A German physicist and mathematician, considered one of the central
founders of the science of thermodynamics.  By his restatement of
Sadi Carnot's principle known as the Carnot cycle, he gave the theory
of heat a truer and sounder basis.
"""

from __future__ import division, print_function, absolute_import

import time
import datetime as dt

from ligmos.workers import connSetup

from ultimonitor import apitools as api
from ultimonitor import confparser, printer


def startCollections(cDict, db=None, loopTime=60):
    """
    """
    # Temperature timestamps are in seconds since boot ... kinda.
    #   It *looks* like Ultimaker uses time.monotonic() in a lot of places,
    #   and the reference point for that is *technically* undefined according
    #   to the python docs; in practice it's probably close enough, though
    #   it's worth noting that it's *immune* to NTP updates and system
    #   clock changes in general.
    uptimeSec = api.queryChecker(cDict['printer'].ip, "/system/uptime")
    if uptimeSec != {}:
        # You may be tempted to choose .utcnow() instead of now(); but,
        #   that'd be a mistake.  Influx tries to be fancy for you,
        #   so it's easier to just get the regular time and hope for the best
        #   Otherwise you'll be tracing UTC offsets in the dashboard(s)
        #   for literally ever, which is the worst.
        boottimeUTC = dt.datetime.now() - dt.timedelta(seconds=uptimeSec)
    else:
        boottimeUTC = None

    while True:
        # Do a check of everything we care about
        stats = printer.statusCheck(cDict['printer'].ip)

        # Did our status check work?
        if stats != {}:
            # Collect the temperatures
            tempPkts = printer.tempStats(cDict['printer'].ip,
                                         timeoffset=boottimeUTC)

            # Collect the overall system info
            sysPkts = printer.systemStats(cDict['printer'].ip)

            if db is not None:
                if tempPkts != []:
                    try:
                        db.singleCommit(tempPkts,
                                        table=db.tablename,
                                        timeprec='ms')
                    except Exception as e:
                        # Errors seen so far:
                        # influxdb.exceptions.InfluxDBServerError
                        print("DATABASE COMMIT ERROR!")
                        print(str(e))
                if sysPkts != []:
                    try:
                        db.singleCommit(sysPkts,
                                        table=db.tablename,
                                        timeprec='ms')
                    except Exception as e:
                        # Errors seen so far:
                        # influxdb.exceptions.InfluxDBServerError
                        print("DATABASE COMMIT ERROR!")
                        print(str(e))

        print("Sleeping for %f ..." % (loopTime))
        for _ in range(int(loopTime)):
            time.sleep(1)


if __name__ == "__main__":
    conffile = './config/ultimonitor.conf'
    cDict = confparser.parseConf(conffile)

    # Set up our database object
    #   With contortions because I'm not using my own API in the usual way
    db = connSetup.connIDB({'database': cDict['database']})['database']
    db.tablename = "um3e"

    startCollections(cDict, db=db)
