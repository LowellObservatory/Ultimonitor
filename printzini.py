
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

import time

from ligmos.utils import confparsers
from ultimonitor import printer, email, leds


if __name__ == "__main__":
    conffile = 'ultimonitor.conf'
    pConf = confparsers.rawParser(conffile)

    # Some renames
    apiid = pConf['printerSetup']['apiid']
    apikey = pConf['printerSetup']['apikey']
    printerip = pConf['printerSetup']['ip']

    smtpserver = pConf['email']['smtpserver']
    fromaddr = pConf['email']['fromaddr']
    statusemail = pConf['email']['statusemail']

    # This provides a map between the colors defined above and the
    #   actual values that the Ulimaker 3 Extended may return while printing
    #   or just in general. If printing, the printing status is used, but
    #   this is a dict of all status values that I could figure out
    hsvCols = leds.pallettBobRoss()
    statusColors = {"idle": "PrussianBlue",
                    "printing": "TitaniumWhite",
                    "pausing": "IndianYellow",
                    "paused": "CadmiumYellow",
                    "resuming": "IndianYellow",
                    "pre_print": "SapGreen",
                    # "pre_print": "PhthaloGreen",
                    "post_print": "BrightBlue",
                    "wait_cleanup": "BrightGreen",
                    "error": "BrightRed",
                    "maintenance": "CadmiumYellow",
                    "booting": "PhthaloGreen"}

    # Default sleep interval of 1 minute
    interval = 1.*60.

    # A blank job to compare against
    pJob = {"JobParameters": {"UUID": 8675309}}

    while True:
        # Do a check of everything we care about
        stats = printer.statusCheck(printerip)

        # Is there an active print job?
        if stats['Status'] == 'printing':
            # Is this the same job we saw last time in the loop?
            if stats['JobParameters']['UUID'] != pJob['JobParameters']['UUID']:
                print("New job found!")

                # Clear our temperature stats
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

                # Set this job as the one to watch now
                pJob = stats

                # Notification trackers
                notices = {"start": False,
                           "done10": False,
                           "done50": False,
                           "done90": False,
                           "end": False}

            curProg = stats['JobParameters']['Progress']
            curJobName = stats['JobParameters']['Name']
            # Just take the first part of the UUID so it's not so long...
            curJobID = stats['JobParameters']['UUID'].split("-")[0]

            # Collect the temperature statistics, but only bother if
            #   we're actually in progress. I set the threshold
            #   to be > 0.5 so the extruders and bed should already
            #   be self-regulating, but if it takes < 1 minute to get
            #   to this percentage complete, they'll still have big
            #   deviations
            if curProg > 0.5 and curProg < 100.:
                retTemps = printer.tempStats(printerip)
                tstats, dstats = printer.collapseStats(retTemps, tstats)
                tempPerformance = printer.formatStatus(dstats)

                # Decision tree time!
                msg = None
                if curProg >= 0. and notices['start'] is False:
                    print("Notify that the print is started")
                    notices['start'] = True
                    msg = email.makeEmailUpdate('start',
                                                curJobID,
                                                curJobName,
                                                strStatus,
                                                fromaddr, statusemail)
                    email.sendMail(msg, smtploc=smtpserver)

                elif curProg >= 10. and notices['done10'] is False:
                    print("Notify that the print is 10%% done")
                    notices['done10'] = True
                    msg = email.makeEmailUpdate('done10',
                                                curJobID,
                                                curJobName,
                                                tempPerformance,
                                                fromaddr, statusemail)
                    email.sendMail(msg, smtploc=smtpserver)

                elif curProg >= 50. and notices['done50'] is False:
                    print("Notify that the print is 50%% done")
                    notices['done50'] = True
                    msg = email.makeEmailUpdate('done50',
                                                curJobID,
                                                curJobName,
                                                tempPerformance,
                                                fromaddr, statusemail)
                    email.sendMail(msg, smtploc=smtpserver)

                elif curProg >= 90. and notices['done90'] is False:
                    print("Notify that the print is 90%% done")
                    notices['done90'] = True
                    msg = email.makeEmailUpdate('done90',
                                                curJobID,
                                                curJobName,
                                                tempPerformance,
                                                fromaddr, statusemail)
                    email.sendMail(msg, smtploc=smtpserver)

                # NOTE
                # THIS WILL NEVER OCCUR AS WRITTEN!
                # FIX ASAP
                elif curProg == 100. and notices['end'] is False:
                    print("Notify that the print is done")
                    notices['end'] = True
                    # In addition to the temperature performance, add in the
                    #   print duration as well.
                    endStr = ""
                    msg = email.makeEmailUpdate('end',
                                                curJobID,
                                                curJobName,
                                                tempPerformance,
                                                fromaddr, statusemail)
                    email.sendMail(msg, smtploc=smtpserver)

                print("Job %s is %f %% complete" %
                      (stats['JobParameters']['UUID'],
                       stats['JobParameters']['Progress']))
                print("State: %s" % (stats['JobParameters']['JobState']))
                print("Temperature statistics:")
                print(tempPerformance)
            elif curProg == 100.:
                # This means when we started, the print was already done!
                #   Don't do anything in this case.
                print("Job %s is 100%% complete already..." %
                      (stats['JobParameters']['UUID']), end='')
                print("Awaiting job cleanup.")

            # Need this to set the LED color appropriately
            actualStatus = stats['JobParameters']['JobState']
        else:
            actualStatus = stats['Status']

        leds.ledCheck(apiid, apikey, printerip, hsvCols,
                      statusColors, actualStatus)

        # print("Sleeping for %f seconds..." % (interval))
        time.sleep(interval)
