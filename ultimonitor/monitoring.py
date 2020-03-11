# -*- coding: utf-8 -*-
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#  Created on 18 Feb 2020
#
#  @author: rhamilton

"""One line description of module.

Further description.
"""

from __future__ import division, print_function, absolute_import

import time
from datetime import datetime as dt

import johnnyfive as j5

from . import email as emailHelper
from . import leds, printer, classes


def notificationTree(stats, actualStatus, notices, curProg, prevProg):
    """
    """
    if notices['preamble'] is False:
        print("Collecting print setup information ...")
        strStatus = printer.formatStatus(stats)
        notices['preamble'] = True

    retTemps = {}

    emailFlag = False
    noteKey = None
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
    if actualStatus.lower() in ['post_print', 'wait_cleanup']:
        if prevProg == -9999 or prevProg == 100.:
            # This means when we started, the print was done!
            #   Don't do anything in this case.
            print("Job %s is 100%% complete already..." %
                  (stats['JobParameters']['UUID']), end='')
            print("Awaiting job cleanup...")
            print("Skipping notification for job completion")
            emailFlag = False
    else:
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

            # if prevProg == -9999 or prevProg == 100.:
            #     # This means when we started, the print was done!
            #     #   Don't do anything in this case.
            #     print("Job %s is 100%% complete already..." %
            #           (stats['JobParameters']['UUID']), end='')
            #     print("Awaiting job cleanup...")
            #     print("Skipping notification for job completion")
            #     emailFlag = False

            # This state also means that we have no temp. stats.
            #   to report, so set the details string empty
            deets = ""

    return emailFlag, noteKey, deets


def checkJob(stats, pJob, notices):
    """
    """
    # Is this the same job we saw last time in the loop?
    if stats['JobParameters']['UUID'] != pJob['JobParameters']['UUID']:
        print("New job found!")
        thisJob = classes.jobInProgress()

        # We store the reported start timestamp, even though
        #   it can be extremely wrong if the printer is turned on and
        #   can't get any internet access, which causes NTP to fail.
        #
        # Convert this into a comparable datetime object. Assume
        #   that it's UTC, because this is science god damn it.
        reportedTime = stats['JobParameters']['TimeStart']
        thisJob.reportedTime = dt.strptime(reportedTime,
                                           "%Y-%m-%dT%H:%M:%S")
        thisJob.foundTime = dt.utcnow()

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


def idbTempQuery():
    """
    """
    pass


def monitorUltimaker(cDict, statusMap, statusColors, runner,
                     loopInterval=30,
                     squashEmail=False,
                     squashPiCam=False,
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

    # We use runner here to exit in a sensible way if any signals come up
    while runner.halt is False:
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
            print()
            print("flowState: %s" % (flowStateWords))
            print("/printer/state: %s" % (stats['Status']))
            # If we're not actually printing, it won't be possible to get
            #   the state from the print_job endpoint because it'll be blank!
            if stats['JobParameters'] != {}:
                printjobState = stats['JobParameters']['JobState']
                print("/print_job/state: %s" % (printjobState))
            print()

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
                if actualStatus.lower() in ['printing',
                                            'pausing', 'paused', 'resuming',
                                            'post_print', 'wait_cleanup']:
                    emailFlag, noteKey, deets = notificationTree(stats,
                                                                 actualStatus,
                                                                 notices,
                                                                 curProg,
                                                                 prevProg)

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
                            j5.email.sendMail(msg,
                                              smtploc=email.host,
                                              port=email.port,
                                              user=email.user,
                                              passw=email.password)

                # Need this to set the LED color appropriately
                actualStatus = stats['JobParameters']['JobState']

                # Update the progress since we're printing
                print("Previous Progress: ", prevProg)
                print("Current Progress: ", curProg)
                prevProg = curProg
        else:
            print("PRINTER UNREACHABLE!")

        # Take a nap in our infinite loop
        if runner.halt is False:
            print("Sleeping for %d seconds..." % (int(loopInterval)))
            # Sleep for bigsleep, but in small chunks to check abort
            for _ in range(int(loopInterval)):
                time.sleep(1)
                if runner.halt is True:
                    break
