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

from ultimonitor import confparser, printer


def setupStats(stats):
    """
    """
    # Clear our temperature stats
    #   I know, I know, this sucks. This is a prototype!
    tstats = {"Temperature0": {"median": [],
                               "stddev": [],
                               "deltaavg": [],
                               "deltamin": [],
                               "deltamax": [],
                               "deltastd": []},
              "Temperature1": {"median": [],
                               "stddev": [],
                               "deltaavg": [],
                               "deltamin": [],
                               "deltamax": [],
                               "deltastd": []},
              "Bed": {"median": [],
                      "stddev": [],
                      "deltaavg": [],
                      "deltamin": [],
                      "deltamax": [],
                      "deltastd": []},
              "CalculationTime": 0.
              }

    # Print the status to the log, but also get a string
    #   representation that can be sent via email
    strStatus = printer.formatStatus(stats)
    print(strStatus)

    return tstats, strStatus


def startCollections(cDict):
    """
    """
    while True:
        # Do a check of everything we care about
        stats = printer.statusCheck(cDict['printer'].ip)

        # Did our status check work?
        if stats != {}:
            tstats, strStatus = setupStats(stats)
            retTemps = printer.tempStats(cDict['printer'].ip)
            tstats, dstats = printer.collapseStats(retTemps,
                                                   tstats)
            deets = printer.formatStatus(dstats)
            print(deets)


if __name__ == "__main__":
    conffile = 'ultimonitor.conf'
    cDict = confparser.parseConf(conffile)

    startCollections(cDict)