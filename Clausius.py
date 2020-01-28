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

from ligmos.utils import packetizer
from ligmos.workers import connSetup

from ultimonitor import apitools as api
from ultimonitor import confparser, printer


def tempStats(printerip, timeoffset=None):
    """
    Query the printer for temperatures, and format/prepare them for storage.

    Entirely designed for putting into an influxdb database. If you want
    another database type, well, point it at a different formatting
    function in the conditional check on tres.
    """
    if isinstance(timeoffset, dt.datetime):
        print("Applying datetime offset: ", timeoffset)
    elif isinstance(timeoffset, float) or isinstance(timeoffset, int):
        print("Applying scalar/float offset: ", timeoffset)
        print("THIS IS AS YET UNHANDLED, OOPS")
        raise NotImplementedError

    # With what looks like a sample rate of ~10 Hz, 800 samples will give
    #   me ~80 seconds worth of temperature data.  For a query interval of
    #   60 seconds, which could vary depending on some picture stuff, this
    #   will be a pretty good representation of the performance/stability.
    nsamps = 800
    endpoint = "/printer/diagnostics/temperature_flow/%d" % (nsamps)

    # This query is a house of cards; if it fails because the printer
    #   is unreachable, literally everything will implode. So check that
    #   the return value isn't empty!!!
    tres = api.queryChecker(printerip, endpoint)

    if tres != {}:
        # For the Ultimaker 3e, the flow sensor hardware was removed before
        #   the printer shipped so the following are always 0 or 65535;
        #   We exclude them from the results because that's annoying.
        # NOTE: case isn't checked, so they must be *exact* matches!
        #       Also - "Time" is skipped because we store that differently
        bklst = ['Time',
                 'flow_sensor0', 'flow_steps0',
                 'flow_sensor1', 'flow_steps1']

        allpkts = []

        for i, points in enumerate(tres):
            # At this point, if the query is successful, tres is a list of
            #   lists,  the first of which is the labels and the rest are
            #   lists of values matching those labels.
            if i == 0:
                flabs = points
                # Translate the blacklisted labels to
                if bklst != []:
                    gi = [k for k, lab in enumerate(flabs) if lab not in bklst]
                else:
                    gi = []
            else:
                # Make an influxdb packet, but first do some contortions
                #   to make the timestamp a real timestamp rather than
                #   just an offset from boot
                ts = timeoffset + dt.timedelta(seconds=points[0])
                # We need to strip out the
                # Convert it to nanoseconds for influx
                #   NOTE: It CAN NOT be a float! Must be an Int :(
                ts = int(float(ts.strftime("%s.%f"))*1e3)

                # Grab the non-blacklisted items and construct our packet
                #   I can't think of a good way to put this into a set of
                #   non-confusing list comprehensions so I'm breaking it out
                fields = {}
                for idx in gi:
                    fields.update({flabs[idx]: points[idx]})

                pkt = packetizer.makeInfluxPacket(meas=['temperatures'],
                                                  ts=ts, fields=fields,
                                                  tags=None)
                # Have to do pkt[0] because makeInfluxPacket is still
                #   annoying and quirky
                allpkts.append(pkt[0])
    else:
        # This happens when the printer query fails
        allpkts = []

    return allpkts


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
            tempPkts = tempStats(cDict['printer'].ip, timeoffset=boottimeUTC)

            if db is not None:
                if tempPkts != []:
                    db.singleCommit(tempPkts,
                                    table=db.tablename,
                                    timeprec='ms')

        print("Sleeping for %f ..." % (loopTime))
        for _ in range(int(loopTime)):
            time.sleep(1)


if __name__ == "__main__":
    conffile = 'ultimonitor.conf'
    cDict = confparser.parseConf(conffile)

    # Set up our database object
    #   With contortions because I'm not using my own API in the usual way
    db = connSetup.connIDB({'database': cDict['database']})['database']

    db.tablename = "um3e"

    startCollections(cDict, db=db)
