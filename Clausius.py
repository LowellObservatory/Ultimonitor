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

from ultimonitor import confparser, printer


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


def startCollections(cDict, loopTime=60.):
    """
    """
    while True:
        # Do a check of everything we care about
        stats = printer.statusCheck(cDict['printer'].ip)

        # Did our status check work?
        if stats != {}:
            retTemps = tempStats(cDict['printer'].ip)

            print(retTemps)
        print("Sleeping for %f ..." % (loopTime))
        time.sleep(loopTime)


if __name__ == "__main__":
    conffile = 'ultimonitor.conf'
    cDict = confparser.parseConf(conffile)

    startCollections(cDict)
