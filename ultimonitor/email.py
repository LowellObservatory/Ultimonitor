# -*- coding: utf-8 -*-
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#  Created on 20 Aug 2019
#
#  @author: rhamilton

"""It's the email, the email, what what, the email.
"""

from __future__ import division, print_function, absolute_import

import imghdr

import requests.exceptions as rqex

import johnnyfive as j5

from . import cameras


def makeEmailUpdate(etype, jobid, jobname, strStat, emailConfig,
                    picam=None, ulticam=None):
    """
    """
    # First make sure we have at least a null string for the
    #   standard footer that is included with every email
    if emailConfig is not None:
        eFrom = emailConfig.user
        eTo = emailConfig.toaddr

        # Read in the footer, if there is one
        if emailConfig.footer is None:
            footer = ""
        else:
            footer = str(emailConfig.footer)
        if etype == "start":
            subject = "Print job '%s' (%s) started!" % (jobname, jobid)
            body = "Hello! I am the Great Printzini!"
            body += "  I have discovered a brand new 3D print job!"
            body += "\nHere are the details that the spirits shared:"
        elif etype == "done10":
            subject = "Print job '%s' (%s) 10%% complete!" % (jobname, jobid)
            body = "Hello again! The print job appears to be still going."
            body += "  I'm not smart enough to know if it's *actually* going"
            body += " ok though, so you should probably check for any adhesion"
            body += " or stringing problems!"
            body += "\nHere is the latest on temperature performance:"
        elif etype == "done50":
            subject = "Print job '%s' (%s) 50%% complete!" % (jobname, jobid)
            body = "Hello again! Congratulations on getting this far!"
            body += "\nHere is the latest on temperature performance:"
        elif etype == "done90":
            subject = "Print job '%s' (%s) 90%% complete!" % (jobname, jobid)
            body = "Hello again! Wow! It's almost done!"
            body += "\nHere is the latest on temperature performance:"
        elif etype == 'end':
            subject = "Print job '%s' (%s) 100%% complete!" % (jobname, jobid)
            body = "Hello again! It's complete! Please come fetch your print!"
            body += "\n\nRemember to acknowledge/click the 'Print Removed'"
            body += " button on the printer's screen! I won't"
            body += " know you're really done otherwise!"
            body += "\nHere are the final temperature statistics:"

        # Now append the rest of the stuff
        body += "\n\n"
        body += strStat
        body += "\n\n"
        body += footer
        body += "\n\nYour 3D pal, \nThe Great Printzini"

        msg = j5.email.constructMail(subject, body, eFrom, eTo,
                                     fromname=emailConfig.fromname)

        # Now grab and attach the images, if they were requested
        if ulticam is not None:
            # It's really just an http GET request so it's easy
            try:
                img = cameras.grab_ultimaker(ulticam.ip)
            except rqex.ReadTimeout:
                print("Ultimaker camera failed to respond!")
                print("Badness 10000")
                img = None
            if img is not None:
                # Attach it to the message
                msg.add_attachment(img.content, maintype='image',
                                   subtype=imghdr.what(None, img.content),
                                   filename="UltimakerSideView.jpg")

        if picam is not None:
            snapname = cameras.piCamCapture(picam)

            if snapname is not None:
                with open(snapname, 'rb') as pisnap:
                    piimg = pisnap.read()
                    msg.add_attachment(piimg, maintype='image',
                                       subtype=imghdr.what(None, piimg),
                                       filename="UltimakerTopView.png")
            else:
                print("PiCamera capture failed!")
    else:
        print("Emails disabled; returning.")
        msg = None

    return msg
