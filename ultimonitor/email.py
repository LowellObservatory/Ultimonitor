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
import smtplib
from email.message import EmailMessage

from . import cameras


def sendMail(message, smtploc='localhost', port=25):
    """
    This assumes that the SMTP server has no authentication, and that
    message is an instance of EmailMessage.
    """

    print("Sending email...")

    # TODO: catch the right timeout exception here
    with smtplib.SMTP(smtploc, port, timeout=10.) as server:
        # retmsg = server.send_message(message)
        pass

    print(message)
    print(retmsg)
    print("Email sent!")


def constructMail(subject, body, fromaddr, toaddr):
    """
    """
    msg = EmailMessage()
    msg['From'] = fromaddr
    msg['To'] = toaddr

    # Make sure replies go to the list, not to this 'from' address
    msg.add_header('reply-to', toaddr)

    msg['Subject'] = subject
    msg.set_content(body)

    return msg


def makeEmailUpdate(etype, jobid, jobname, strStat, fromaddr, toaddr,
                    picam=None, ulticam=None, footer=None):
    """
    """
    # First make sure we have at least a null string for the
    #   standard footer that is included with every email
    if footer is None:
        footer = ""

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

    msg = constructMail(subject, body, fromaddr, toaddr)

    # Now grab and attach the images, if they were requested
    if ulticam is not None:
        # It's really just an http GET request so it's easy
        img = cameras.grab_ultimaker(ulticam)
        if img is not None:
            # Attach it to the message
            msg.add_attachment(img.content, maintype='image',
                               subtype=imghdr.what(None, img.content),
                               filename="UltimakerSideView.jpg")

    if picam is True:
        snapname = cameras.piCamCapture(picam)
        if snapname is not None:
            with open(snapname, 'rb') as pisnap:
                piimg = pisnap.read()
                msg.add_attachment(piimg, maintype='image',
                                   subtype=imghdr.what(None, piimg),
                                   filename="UltimakerTopView.png")
        else:
            print("PiCamera capture failed! Is there even a Pi camera?")

    return msg
