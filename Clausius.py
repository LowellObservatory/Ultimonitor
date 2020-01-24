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
        #   We exclude them from the results because that's annoying
        blacklist = ['flow_sensor0', 'flow_steps0',
                     'flow_sensor1', 'flow_steps1']

        for i, points in enumerate(tres):
            if i == 0:
                # Set up our returned dict
                tdict = {}
                for key in points:
                    if key not in blacklist:
                        tdict.update({key: []})
                # Store all the labels so we can check against them later
                flabs = points
            else:
                for j, temp in enumerate(points):
                    if j == 0:
                        # Apply our time offset
                        temp = timeoffset + dt.timedelta(seconds=temp)
                        # Convert it to seconds for influx
                        temp = float(temp.strftime("%s.%f"))
                    try:
                        tdict[flabs[j]].append(temp)
                    except KeyError:
                        # This means that the column/key was blacklisted
                        #   so we just pass silently onwards
                        # print("ignoring blacklisted field", flabs[j])
                        pass
    else:
        # This happens when the printer query fails
        tdict = {}

    return tdict


def startCollections(cDict, db=None, loopTime=60.):
    """
    """
    # Temperature timestamps are in seconds since boot ... kinda.
    #   It *looks* like Ultimaker uses time.monotonic() in a lot of places,
    #   and the reference point for that is *technically* undefined according
    #   to the python docs; in practice it's probably close enough, though
    #   it's worth noting that it's *immune* to NTP updates and system
    #   clock changes in general.
    uptimeSec = api.queryChecker(cDict['printer'].ip, "/system/uptime")
    boottimeUTC = dt.datetime.utcnow() - dt.timedelta(seconds=uptimeSec)
    while True:
        # Do a check of everything we care about
        stats = printer.statusCheck(cDict['printer'].ip)

        # Did our status check work?
        if stats != {}:
            retTemps = tempStats(cDict['printer'].ip, timeoffset=boottimeUTC)

            # Make the influx packet that will be stored
            #   First pop out the timestamp column so we can pass it in proper
            ts = retTemps.pop("Time")
            pkt = packetizer.makeInfluxPacket(meas=['temperatures'],
                                              ts=ts,
                                              fields=retTemps)

            if db is not None:
                print("Packet for database:")
                print(pkt)

        print("Sleeping for %f ..." % (loopTime))
        time.sleep(loopTime)


if __name__ == "__main__":
    conffile = 'ultimonitor.conf'
    cDict = confparser.parseConf(conffile)

    # Set up our database object
    #   With contortions because I'm not using my own API in the usual way
    db = connSetup.connIDB({'database': cDict['database']})['database']

    db.tablename = "um3e"

    startCollections(cDict, db=db)
