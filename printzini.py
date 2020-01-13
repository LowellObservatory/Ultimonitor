
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

    # Read in the footer file as a text string
    try:
        with open(pConf['email']['footer'], 'r') as f:
            footer = f.read()
    except (OSError, IOError):
        footer = None

    # A quick way to disable email alerts; should put this in the config?
    emailSquasher = False

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
                    "post_print": "BrightBlue",
                    "wait_cleanup": "BrightGreen",
                    "error": "BrightRed",
                    "maintenance": "CadmiumYellow",
                    "booting": "PhthaloGreen"}

    # Default sleep interval of 1 minute
    interval = 1.*60.

    # Initial parameters to compare against
    pJob = {"JobParameters": {"UUID": 8675309}}
    prevProg = -9999

    while True:
        # Do a check of everything we care about
        stats = printer.statusCheck(printerip)

        # Is there an active print job?
        if stats['Status'] == 'printing':
            # Is this the same job we saw last time in the loop?
            if stats['JobParameters']['UUID'] != pJob['JobParameters']['UUID']:
                print("New job found!")

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
            #   deviations. Oh well.
            msg = None
            noteKey = None
            emailFlag = False
            if curProg > 0.5 and curProg < 100.:
                retTemps = printer.tempStats(printerip)
                tstats, dstats = printer.collapseStats(retTemps, tstats)
                deets = printer.formatStatus(dstats)

                # Decision tree time!
                if curProg >= 0. and notices['start'] is False:
                    print("Notify that the print is started")
                    noteKey = 'start'
                    emailFlag = True
                    # The first time thru gets a more detailed header, that
                    #   we actually already set above. We're just overriding
                    #   the shortened version here
                    deets = strStatus

                elif curProg >= 10. and notices['done10'] is False:
                    print("Notify that the print is 10%% done")
                    noteKey = 'done10'
                    emailFlag = True

                elif curProg >= 50. and notices['done50'] is False:
                    print("Notify that the print is 50%% done")
                    noteKey = 'done50'
                    emailFlag = True

                elif curProg >= 90. and notices['done90'] is False:
                    print("Notify that the print is 90%% done")
                    noteKey = 'done90'
                    emailFlag = True

            elif curProg == 100. and notices['end'] is False:
                print("Notify that the print is done")
                noteKey = 'end'
                emailFlag = True

                # In addition to the temperature performance, add in the
                #   print duration as well.
                print("Job %s is %f %% complete" %
                      (stats['JobParameters']['UUID'],
                       stats['JobParameters']['Progress']))
                print("State: %s" % (stats['JobParameters']['JobState']))
                print("Temperature statistics:")
                print(deets)

            elif curProg == 100. and (prevProg == -9999 or prevProg == 100.):
                # This means when we started, the print was already done!
                #   Don't do anything in this case.
                print("Job %s is 100%% complete already..." %
                      (stats['JobParameters']['UUID']), end='')
                print("Awaiting job cleanup.")

            # Now check the states that we could have gotten into by the above
            if noteKey is not None:
                notices[noteKey] = True
                print(deets)
                if emailFlag is True and emailSquasher is False:
                    print(noteKey)
                    print(notices[noteKey])
                    print(notices)
                    msg = email.makeEmailUpdate(noteKey,
                                                curJobID,
                                                curJobName,
                                                deets,
                                                fromaddr, statusemail,
                                                picam=None,
                                                ulticam=printerip,
                                                footer=footer)
                    email.sendMail(msg, smtploc=smtpserver)

            # Need this to set the LED color appropriately
            actualStatus = stats['JobParameters']['JobState']
        else:
            # I forget what this is for?  I think a default/initial
            #   state so the ledCheck below doesn't screw up?
            actualStatus = stats['Status']

        # Update the progress
        print("Previous Progress: ", prevProg)
        print("Current Progress: ", curProg)
        prevProg = curProg

        leds.ledCheck(apiid, apikey, printerip, hsvCols,
                      statusColors, actualStatus)

        print("Sleeping for %f seconds..." % (interval))
        time.sleep(interval)
