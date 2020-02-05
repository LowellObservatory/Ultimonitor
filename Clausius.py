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

from ligmos.workers import connSetup

from ultimonitor import confparser, printer


def startCollections(printerip, db=None, loopTime=30):
    """
    """

    while True:
        # Do a check of everything we care about
        stats = printer.statusCheck(printerip)

        # Did our status check work?
        if stats != {}:
            # Collect the temperatures. Remember: nsamps should be slightly
            #   greater than 10xloopTime since the sample rate is 10 Hz
            tempPkts = printer.tempFlow(printerip, nsamps=450)

            # Collect the overall system info
            sysPkts = printer.systemStats(printerip)

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

    printerip = cDict['printerSetup'].ip
    startCollections(printerip, db=db)
