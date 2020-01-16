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

from collections import OrderedDict

import xmltodict
import numpy as np

from . import apitools as api


def getMaterial(printerip, headinfo, extruder=0):
    """
    Don't need API id/key because these are all GET requests
    """
    mat = headinfo['extruders'][extruder]['active_material']['guid']
    matXML = api.queryChecker(printerip, "materials/" + mat)

    # This is a potential failure point to wrap it for now
    try:
        matMeta = xmltodict.parse(matXML)['fdmmaterial']['metadata']['name']
        matProp = xmltodict.parse(matXML)['fdmmaterial']['properties']
    except Exception as err:
        # TODO: Catch the right exception
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

    return material


def statusCheck(printerip):
    """
    Don't need API id/key because these are all GET requests
    """
    returnable = OrderedDict()

    ptype = api.queryChecker(printerip, "system/variant", fill="UNKNOWN")
    pname = api.queryChecker(printerip, "system/name", fill="UNKNOWN")
    firmware = api.queryChecker(printerip, "system/firmware", fill="UNKNOWN")
    sysguid = api.queryChecker(printerip, "system/guid", fill="UNKNOWN")

    returnable.update({"Printer": {"Type": ptype,
                                   "Name": pname,
                                   "SWVersion": firmware,
                                   "GUID": sysguid}})

    status = api.queryChecker(printerip, "printer/status", fill="UNKNOWN")
    returnable.update({"Status": status})

    # We don't store this, but we pull lots of stuff out of it. We treat it
    #   slightly differently as the above since there are multiple values
    #   to set to "UNKNOWN" in case the printer is unreachable
    headinfo = api.queryChecker(printerip, "printer/heads/0")
    if headinfo != {}:
        ext1 = headinfo['extruders'][0]['hotend']['id']
        ext2 = headinfo['extruders'][1]['hotend']['id']

        material1 = getMaterial(printerip, headinfo, extruder=0)
        material2 = getMaterial(printerip, headinfo, extruder=1)
    else:
        ext1 = "UNKNOWN"
        material1 = "UNKNOWN"
        ext2 = "UNKNOWN"
        material2 = "UNKNOWN"

    bedtype = api.queryChecker(printerip, "printer/bed/type", fill="UNKNOWN")

    returnable.update({"PrintSetup": {"Extruder1": ext1,
                                      "Material1": material1,
                                      "Extruder2": ext2,
                                      "Material2": material2,
                                      "BedType": bedtype}})

    if status == "printing":
        # Query some more!
        bedtemp = api.queryChecker(printerip, "printer/bed/temperature")
        if bedtemp != {}:
            ext1temps = headinfo['extruders'][0]['hotend']['temperature']
            ext2temps = headinfo['extruders'][1]['hotend']['temperature']
        else:
            ext1temps = ""
        printjob = api.queryChecker(printerip, "print_job")

        jobname = printjob['name']
        jobstart = printjob['datetime_started']
        jobsource = printjob['source']
        jobuser = printjob['source_user']
        jobuuid = printjob['uuid']

        elapsedtime = printjob['time_elapsed']/60./60.
        estimatedtime = printjob['time_total']/60./60.
        progress = printjob['progress']*100
        jobstate = printjob['state']

        jp = {"Name": jobname,
              "TimeStart": jobstart,
              "Source": jobsource,
              "Username": jobuser,
              "UUID": jobuuid,
              "BedTemp": bedtemp['current'],
              "BedTempSetp": bedtemp['target'],
              "Extruder1Temp": ext1temps['current'],
              "Extruder1Setp": ext1temps['target'],
              "Extruder2Temp": ext2temps['current'],
              "Extruder2Setp": ext2temps['target'],
              "ElapsedTime": elapsedtime,
              "EstimatedDuration": estimatedtime,
              "JobState": jobstate,
              "Progress": progress}

        returnable.update({"JobParameters": jp})
    else:
        # This is just a reminder; if it's not printing, then there
        #   will be *NO* JobParameters key in the dict!
        print("Not printing!")
        print(status)

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
                elif key in ['BedTemp', 'BedTempSetp',
                             'Extruder1Temp', 'Extruder1Setp',
                             'Extruder2Temp', 'Extruder2Setp']:
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


def tempStats(printerip):
    """
    """
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
        # These will likely always be the same so just hard code them so I
        #   don't have to parse them out of the results above
        flabs = ['Time',
                 'temperature0', 'target0', 'heater0',
                 'flow_sensor0', 'flow_steps0',
                 'temperature1', 'target1', 'heater1',
                 'flow_sensor1', 'flow_steps1',
                 'bed_temperature', 'bed_target', 'bed_heater',
                 'active_hotend_or_state']

        # Quick and dirty list comprehension to set up our results dictionary
        tdict = {}
        [tdict.update({key: []}) for key in flabs]

        for points in tres[1:]:
            for i, temp in enumerate(points):
                tdict[flabs[i]].append(temp)

        # Now collapse down some stats
        trange = tdict['Time'][-1] - tdict['Time'][0]

        t0med = np.median(tdict['temperature0'])
        t0std = np.std(tdict['temperature0'])
        t0delta = np.abs(np.array(tdict['target0']) -
                         np.array(tdict['temperature0']))
        t0deltastd = np.std(t0delta)
        t0deltami = np.min(t0delta)
        t0deltama = np.max(t0delta)
        t0deltaa = np.average(t0delta)

        t1med = np.median(tdict['temperature1'])
        t1std = np.std(tdict['temperature1'])
        t1delta = np.abs(np.array(tdict['target1']) -
                         np.array(tdict['temperature1']))
        t1deltastd = np.std(t1delta)
        t1deltami = np.min(t1delta)
        t1deltama = np.max(t1delta)
        t1deltaa = np.average(t1delta)

        bedmed = np.median(tdict['bed_temperature'])
        bedstd = np.std(tdict['bed_temperature'])
        beddelta = np.abs(np.array(tdict['bed_target']) -
                          np.array(tdict['bed_temperature']))
        beddeltami = np.min(beddelta)
        beddeltama = np.max(beddelta)
        beddeltastd = np.std(beddelta)
        beddeltaa = np.average(beddelta)

        # Pack it all into a dict to return and store/report
        retTemps = {"CalculationTime": trange,
                    "Temperature0": {"median": t0med,
                                     "stddev": t0std,
                                     "deltaavg": t0deltaa,
                                     "deltamin": t0deltami,
                                     "deltamax": t0deltama,
                                     "deltastd": t0deltastd},
                    "Temperature1": {"median": t1med,
                                     "stddev": t1std,
                                     "deltaavg": t1deltaa,
                                     "deltamin": t1deltami,
                                     "deltamax": t1deltama,
                                     "deltastd": t1deltastd},
                    "Bed": {"median": bedmed,
                            "stddev": bedstd,
                            "deltaavg": beddeltaa,
                            "deltamin": beddeltami,
                            "deltamax": beddeltama,
                            "deltastd": beddeltastd},
                    }
    else:
        # This happens when the printer query fails
        retTemps = {}

    return retTemps


def collapseStats(currenTemps, tstats):
    """
    """
    for key in tstats:
        # This skips any flat keys
        if isinstance(tstats[key], dict):
            for elem in tstats[key]:
                tstats[key][elem].append(currenTemps[key][elem])
        # This may fail in the future if there are additional
        #   flat keys that aren't cumulative
        elif isinstance(tstats[key], float):
            tstats[key] += currenTemps[key]

    tottime = tstats['CalculationTime']

    # Collapse the stats down into the final metrics
    temp0_deltaavg = np.average(tstats['Temperature0']['deltaavg'])
    temp0_deltastd = np.average(tstats['Temperature0']['deltastd'])
    temp0_deltamin = np.min(tstats['Temperature0']['deltamin'])
    temp0_deltamax = np.max(tstats['Temperature0']['deltamax'])

    temp1_deltaavg = np.average(tstats['Temperature1']['deltaavg'])
    temp1_deltastd = np.average(tstats['Temperature1']['deltastd'])
    temp1_deltamin = np.min(tstats['Temperature1']['deltamin'])
    temp1_deltamax = np.max(tstats['Temperature1']['deltamax'])

    bed_deltaavg = np.average(tstats['Bed']['deltaavg'])
    bed_deltastd = np.average(tstats['Bed']['deltastd'])
    bed_deltamin = np.min(tstats['Bed']['deltamin'])
    bed_deltamax = np.max(tstats['Bed']['deltamax'])

    resultDict = {"CalculationTime": round(tottime, 6),
                  "Extruder0Temp": {"DeviationAvg": round(temp0_deltaavg, 6),
                                    "DeviationSTD": round(temp0_deltastd, 6),
                                    "DeviationMin": round(temp0_deltamin, 6),
                                    "DeviationMax": round(temp0_deltamax, 6)},
                  "Extruder1Temp": {"DeviationAvg": round(temp1_deltaavg, 6),
                                    "DeviationSTD": round(temp1_deltastd, 6),
                                    "DeviationMin": round(temp1_deltamin, 6),
                                    "DeviationMax": round(temp1_deltamax, 6)},
                  "BedTemp": {"DeviationAvg": round(bed_deltaavg, 6),
                              "DeviationSTD": round(bed_deltastd, 6),
                              "DeviationMin": round(bed_deltamin, 6),
                              "DeviationMax": round(bed_deltamax, 6)}
                  }

    return tstats, resultDict
