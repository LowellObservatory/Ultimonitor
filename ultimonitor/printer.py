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

import datetime as dt
from collections import OrderedDict

import xmltodict

from ligmos.utils import packetizer

from . import apitools as api


def systemStats(printerip):
    """
    Query the printer for memory
    """
    endpoint = "/system/memory"
    mem = api.queryChecker(printerip, endpoint)
    if mem != {}:
        mem.update({"free": mem['total'] - mem['used']})

        pkt = packetizer.makeInfluxPacket(meas=['system'],
                                          fields=mem,
                                          tags=None)
    else:
        # Silly.
        pkt = []

    return pkt


def tempFlow(printerip, nsamps=800, debug=False):
    """
    Query the printer for temperatures, and format/prepare them for storage.

    With what looks like a sample rate of ~10 Hz, 800 samples will give
    ~80 seconds worth of temperature data.  For a query interval of
    60 seconds, which could vary depending on some picture stuff, this
    will be a pretty good representation of the performance/stability.

    Entirely designed for putting into an influxdb database. If you want
    another database type, well, point it at a different formatting
    function in the conditional check on tres.
    """
    boottime = None
    # Temperature timestamps are in seconds since boot ... kinda.
    #   It *looks* like Ultimaker uses time.monotonic() in a lot of places,
    #   and the reference point for that is *technically* undefined according
    #   to the python docs; in practice it's probably close enough, though
    #   it's worth noting that it's *immune* to NTP updates and system
    #   clock changes in general. Ugh.
    uptimeSec = api.queryChecker(printerip, "/system/uptime")
    if uptimeSec != {}:
        # You may be tempted to choose .utcnow() instead of now(); but,
        #   that'd be a mistake.  Influx tries to be fancy for you,
        #   so it's easier to just get the regular time and hope for the best
        #   Otherwise you'll be tracing UTC offsets in the dashboard(s)
        #   for literally ever, which is the worst.
        boottime = dt.datetime.now() - dt.timedelta(seconds=uptimeSec)
        if debug is True:
            print("Calculated datetime data offset: ", boottime)

    # This query is a house of cards; if it fails because the printer
    #   is unreachable, literally everything will implode. So check that
    #   the return value isn't empty!!!
    endpoint = "/printer/diagnostics/temperature_flow/%d" % (nsamps)
    tres = api.queryChecker(printerip, endpoint)

    if tres != {} and boottime is not None:
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
                ts = boottime + dt.timedelta(seconds=points[0])
                # Convert it to milliseconds for influx
                #   NOTE: It CAN NOT be a float! Must be an Int :(
                #         If we omit ndigits to round() it'll return an int
                ts = round(float(ts.strftime("%s.%f"))*1e3)

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
        print("ERROR: Printer query failed!")
        # This happens when the printer query fails
        allpkts = []

    return allpkts


def getMaterial(printerip, headinfo, extruder=0):
    """
    Don't need API id/key because these are all GET requests
    """
    mat = headinfo['extruders'][extruder]['active_material']['guid']
    mXML = api.queryChecker(printerip, "materials/" + mat)

    # Make sure the material query didn't croak for some reason
    if mXML != {}:
        # This is a potential failure point to wrap it for now
        try:
            matMeta = xmltodict.parse(mXML)['fdmmaterial']['metadata']['name']
            matProp = xmltodict.parse(mXML)['fdmmaterial']['properties']
        except Exception as err:
            # TODO: Catch the right exception for xmltodict
            print(str(err))
            matMeta = None
            matProp = None

        if matMeta is not None:
            matBrand = matMeta['brand']
            matName = matMeta['material']
            matColor = matMeta['color']
        else:
            matBrand, matName, matColor = "UNKNOWN", "UNKNOWN", "UNKNOWN"

        if matProp is not None:
            matDiameter = matProp['diameter']
            matDensity = matProp['density']
        else:
            matDiameter, matDensity = "UNKNOWN", "UNKNOWN"

        material = "%s %s %s" % (matName, matBrand, matColor)
        material += " (%s mm, %s g/cm^3)" % (matDiameter, matDensity)
    else:
        material = "UNKNOWN"

    return material


def getPrinterInfo(printerip):
    """
    All of these should be GET requests not needing authentication.

    They also shouldn't ever really change, so it stands alone out here
    and will be called once at startup
    """
    returnable = OrderedDict()

    # We use the fill parameter here since these are all single replies;
    #   it's easier to just set them to UNKNOWN if the query fails this way
    ptype = api.queryChecker(printerip, "system/variant", fill="UNKNOWN")
    pname = api.queryChecker(printerip, "system/name", fill="UNKNOWN")
    firmware = api.queryChecker(printerip, "system/firmware", fill="UNKNOWN")
    sysguid = api.queryChecker(printerip, "system/guid", fill="UNKNOWN")

    returnable.update({"Printer": {"Type": ptype,
                                   "Name": pname,
                                   "SWVersion": firmware,
                                   "GUID": sysguid}})

    return returnable


def statusCheck(printerip):
    """
    Don't need API id/key because these are all GET requests
    """
    returnable = OrderedDict()

    # Get a few basic updates
    status = api.queryChecker(printerip, "printer/status", fill="UNKNOWN")

    # We don't store this, but we pull lots of stuff out of it. We treat it
    #   slightly differently as the above since there are multiple values
    #   to set to "UNKNOWN" in case the printer is unreachable
    headinfo = api.queryChecker(printerip, "printer/heads/0")
    if headinfo != {}:
        ext1 = headinfo['extruders'][0]['hotend']['id']
        ext2 = headinfo['extruders'][1]['hotend']['id']

        # NOTE: There is an additional paranoia check in these for query fails
        material1 = getMaterial(printerip, headinfo, extruder=0)
        material2 = getMaterial(printerip, headinfo, extruder=1)
    else:
        ext1 = "UNKNOWN"
        material1 = "UNKNOWN"
        ext2 = "UNKNOWN"
        material2 = "UNKNOWN"

    bedtype = api.queryChecker(printerip, "printer/bed/type", fill="UNKNOWN")

    if status == "printing":
        # Yay, we're printing!  Query some more!
        bedtemp = api.queryChecker(printerip, "printer/bed/temperature")
        try:
            if bedtemp != {}:
                ext1temps = headinfo['extruders'][0]['hotend']['temperature']
                ext2temps = headinfo['extruders'][1]['hotend']['temperature']
            else:
                ext1temps = ""
        except Exception as err:
            print("Unexpected error:")
            print(str(err))

        # Another multi-parameter check sequence
        printjob = api.queryChecker(printerip, "print_job")
        if printjob != {}:
            jobname = printjob['name']
            jobstart = printjob['datetime_started']
            jobsource = printjob['source']
            jobuser = printjob['source_user']
            jobuuid = printjob['uuid']

            elapsedtime = printjob['time_elapsed']/60./60.
            estimatedtime = printjob['time_total']/60./60.
            progress = printjob['progress']*100
            jobstate = printjob['state']
        else:
            jobname = "UNKNOWN"
            jobstart = "UNKNOWN"
            jobsource = "UNKNOWN"
            jobuser = "UNKNOWN"
            jobuuid = "UNKNOWN"

            elapsedtime = -1
            estimatedtime = -1
            progress = -1
            jobstate = "UNKNOWN"

        jp = {"Name": jobname,
              "TimeStart": jobstart,
              "Source": jobsource,
              "Username": jobuser,
              "UUID": jobuuid,
              "BedTempSetp": bedtemp['target'],
              "Extruder1Setp": ext1temps['target'],
              "Extruder2Setp": ext2temps['target'],
              "ElapsedTime": elapsedtime,
              "EstimatedDuration": estimatedtime,
              "JobState": jobstate,
              "Progress": progress}
    else:
        # This is just a reminder; if it's not printing, then there
        #   will be *NO* JobParameters key in the dict!
        print("The printer is not printing! Here is it's current status:")
        print(status)
        jp = {}

    # Pack up our results and head home
    returnable.update({"PrintSetup": {"Extruder1": ext1,
                                      "Material1": material1,
                                      "Extruder2": ext2,
                                      "Material2": material2,
                                      "BedType": bedtype}})
    returnable.update({"Status": status})
    returnable.update({"JobParameters": jp})

    return returnable


def formatStatus(stats):
    """
    """
    retStr = ""

    for sect in stats:
        if isinstance(stats[sect], dict):
            retStr += "%s\n" % (sect)
            for key in stats[sect]:
                # Some custom key handling for formatting
                if key in ['ElapsedTime', 'EstimatedDuration']:
                    retStr += "\t%s: %.3f hrs\n" % (key, stats[sect][key])
                elif key == 'Progress':
                    retStr += "\t%s: %.3f %%\n" % (key, stats[sect][key])
                elif key in ['BedTempSetp',
                             'Extruder1Setp', 'Extruder2Setp']:
                    retStr += "\t%s: %.3f C\n" % (key, stats[sect][key])
                else:
                    retStr += "\t%s: %s\n" % (key, stats[sect][key])
        elif isinstance(stats[sect], str):
            retStr += "\t%s: %s\n" % (sect, stats[sect])
        elif isinstance(stats[sect], float):
            if sect == "CalculationTime":
                retStr += "%s: %.3f min \n\n" % (sect, stats[sect]/60.)
            else:
                retStr += "\t%s: %f\n" % (sect, stats[sect])

    return retStr
