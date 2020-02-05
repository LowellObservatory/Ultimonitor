# -*- coding: utf-8 -*-
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#  Created on 17 Aug 2019
#
#  @author: rhamilton

"""The Great Printzini

Monitor for the Ultimaker series of 3D printers, using their supported API.
Also supports a Raspberry Pi camera to take additional pictures of the print.
"""

from __future__ import division, print_function, absolute_import

import time

from ultimonitor import email as emailHelper
from ultimonitor import confparser, printer, leds


def checkJob(stats, pJob, notices):
    """
    """
    # Is this the same job we saw last time in the loop?
    if stats['JobParameters']['UUID'] != pJob['JobParameters']['UUID']:
        print("New job found!")

        # Set this job as the one to watch now
        pJob = stats

        # Notification trackers
        notices = {"preamble": False,
                   "start": False,
                   "done10": False,
                   "done50": False,
                   "done90": False,
                   "end": False}

    return stats, notices


def monitorUltimaker(cDict, statusMap, statusColors, loopInterval=30,
                     squashEmail=False, squashPiCam=False,
                     squashUltiCam=False):
    """
    """
    # Initial parameters to compare against
    pJob = {"JobParameters": {"UUID": 8675309}}
    curProg = -9999
    prevProg = -9999
    notices = None

    # Some renames, also some debugging and squashing of stuff
    printerip = cDict['printerSetup'].ip
    email = None
    if squashEmail is False:
        email = cDict['email']
    picam = None
    if squashPiCam is False:
        picam = cDict['picam']
    ulticam = None
    if squashUltiCam is False:
        ulticam = cDict['printerSetup']

    while True:
        # Do a check of everything we care about
        stats = printer.statusCheck(printerip)

        # Did our status check work?
        if stats != {}:
            # The "printer/status" endpoint is pretty terse, but the
            #   "printer/diagnostics/temperature_flow" endpoint is both
            #   highly detailed (sampled ~10 Hz) and highly specific
            #   with it's "active_hotend_or_state" parameter. Use that.

            # This returns a list of influxdb structured packets; since we
            #   only have one sample, it's a list with len() == 1
            singleFlow = printer.tempFlow(printerip, nsamps=1)[0]
            flowState = singleFlow['fields']['active_hotend_or_state']
            flowStateWords = statusMap[flowState]
            print("flowState: %s\t\t\t/printer/state: %s" % (flowStateWords,
                                                             stats['Status']))

            # We have to do a check in two parts, because some states are from
            #   the lower level printer firmware and some states are from the
            #   higher level Ultimaker software
            if stats['Status'] in ['error', 'maintenance', 'booting']:
                actualStatus = stats['Status']
            else:
                # Use the lower level status since it's more detailed
                actualStatus = flowStateWords

            # Only attempt to change the LED colors if we have a valid status
            if actualStatus.lower() != 'unknown':
                # NOTE: Pass in the entire printer configuration since
                #   this is a PUT action and needs API authentication.
                #   Use actualStatus to capture the full range of states
                leds.ledCheck(cDict['printerSetup'],
                              statusColors, actualStatus)

            # Trigger on the high level status here so I don't have to deal
            #   *all* the possibilities of the low level one
            if stats['Status'] == 'printing':
                # Check if this job is the same as the last job we saw
                pJob, notices = checkJob(stats, pJob, notices)

                curProg = stats['JobParameters']['Progress']
                curJobName = stats['JobParameters']['Name']
                # Just take the first part of the UUID so it's not so long...
                curJobID = stats['JobParameters']['UUID'].split("-")[0]

                # Collect the temperature statistics, but only bother if
                #   we're actually in progress. I set the threshold
                #   to be > 0.5 so the extruders and bed *should* be
                #   regulated already
                msg = None
                deets = None
                noteKey = None
                emailFlag = False

                # Only grab info when we're really printing.
                #   'pre_print' is too early and duration will be missing
                if actualStatus is 'printing':
                    if notices['preamble'] is False:
                        print("Collecting print setup information ...")
                        strStatus = printer.formatStatus(stats)
                        notices['preamble'] = True

                    retTemps = {}
                    deets = ""
                    #
                    # Grab our temperature metrics from the storage
                    #   database that was specified
                    #
                    # retTemps = printer.tempStats(cDict['printer'].ip)
                    # tstats, dstats = printer.collapseStats(retTemps,
                    #                                        tstats)
                    # deets = printer.formatStatus(dstats)
                    #
                    if retTemps == {}:
                        deets = "Unfortunately, the database was unavailable"
                        deets += " when temperature statistics were queried."
                        deets += "\n\nThat's probably not a good thing, but "
                        deets += "it could just mean that the network "
                        deets += "was interrupted unexpectedly. You should "
                        deets += "probably check on stuff!"

                    # Decision tree time!
                    if curProg >= 0. and notices['start'] is False:
                        print("Notify that the print is started")
                        print("Collect the vital statistics")
                        noteKey = 'start'
                        emailFlag = True
                        # The first time thru gets a more detailed header, that
                        #   we actually already set above. We're just
                        #   overloading the shortened version here
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

                        # In addition to the temperature performance,
                        #   add in the print duration as well.
                        print("Job %s is %f %% complete" %
                              (stats['JobParameters']['UUID'],
                               stats['JobParameters']['Progress']))
                        print("State: %s" %
                              (stats['JobParameters']['JobState']))

                        if prevProg == -9999 or prevProg == 100.:
                            # This means when we started, the print was done!
                            #   Don't do anything in this case.
                            print("Job %s is 100%% complete already..." %
                                  (stats['JobParameters']['UUID']), end='')
                            print("Awaiting job cleanup...")
                            print("Skipping notification for job completion")
                            emailFlag = False

                        # This state also means that we have no temp. stats.
                        #   to report, so set the details string empty
                        deets = ""

                # Now check the states that we could have gotten into
                if noteKey is not None:
                    notices[noteKey] = True
                    print(deets)
                    if emailFlag is True:
                        print(noteKey)
                        print(notices[noteKey])
                        print(notices)
                        msg = emailHelper.makeEmailUpdate(noteKey,
                                                          curJobID,
                                                          curJobName,
                                                          deets, email,
                                                          picam=picam,
                                                          ulticam=ulticam)
                        # If squashEmail is True, email will be None
                        if email is not None:
                            emailHelper.sendMail(msg, smtploc=email.host)

                # Need this to set the LED color appropriately
                actualStatus = stats['JobParameters']['JobState']

                # Update the progress since we're printing
                print("Previous Progress: ", prevProg)
                print("Current Progress: ", curProg)
                prevProg = curProg
        else:
            print("PRINTER UNREACHABLE!")

        # Take a nap in our infinite loop
        print("Sleeping for %f seconds..." % (loopInterval))
        for _ in range(int(loopInterval)):
            time.sleep(1)


if __name__ == "__main__":
    conffile = './config/ultimonitor.conf'
    cDict = confparser.parseConf(conffile)

    # A quick way to disable stuff while debugging
    squashEmail = True
    squashPiCam = True
    squashUltiCam = True

    # These are our color options, given as a dict of color names and their
    #   associated HSV (!NOT RGB!) properties which are actually sent to the
    #   case LEDs via the printer API
    hsvCols = leds.pallettBobRoss()

    # The numerical codes are seen in "printer/diagnostics/temperature_flow/"
    #   See also: griffin/printer/drivers/marlin/applicationLayer.py
    # TODO: Figure out if there are additional valid states in 1 thru 9
    flowStateMap = {0: 'printing',
                    10: 'idle',
                    11: 'pausing',
                    12: 'paused',
                    13: 'resuming',
                    14: 'pre_print',
                    15: 'post_print',
                    16: 'wait_cleanup',
                    17: 'wait_user_action'}

    # NOTE: There are 3 additional states (error, maintenance, booting) that
    #   aren't captured in the flowStateMap since they originate elsewhere
    #   in the Ultimaker griffin engine
    statusColors = {"idle": hsvCols["PrussianBlue"],
                    "printing": hsvCols["TitaniumWhite"],
                    "pausing": hsvCols["IndianYellow"],
                    "paused": hsvCols["CadmiumYellow"],
                    "resuming": hsvCols["IndianYellow"],
                    "pre_print": hsvCols["SapGreen"],
                    "post_print": hsvCols["BrightBlue"],
                    "wait_cleanup": hsvCols["BrightGreen"],
                    "wait_user_action": hsvCols["BrightRed"],
                    "error": hsvCols["BrightRed"],
                    "maintenance": hsvCols["CadmiumYellow"],
                    "booting": hsvCols["PhthaloGreen"]}

    # Actually monitor
    monitorUltimaker(cDict, flowStateMap, statusColors, loopInterval=30,
                     squashEmail=squashEmail, squashPiCam=squashPiCam,
                     squashUltiCam=squashUltiCam)
