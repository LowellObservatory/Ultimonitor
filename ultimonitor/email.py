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

import ssl
import imghdr
import socket
import smtplib
from email.message import EmailMessage

from . import cameras


def sendMail(message, smtploc='localhost', port=25, user=None, passw=None):
    """
    This assumes that the SMTP server has no authentication, and that
    message is an instance of EmailMessage.
    """
    # Ultimate return value to know whether we need to try again later
    success = False

    try:
        # This is dumb, but since port is coming from a config file it's
        #   probably still a string at this point.  If we can't int() it,
        #   bail and scream
        port = int(port)
    except ValueError:
        print("FATAL ERROR: Can't interpret port %s!" % (port))
        port = None

    print("Sending email...")
    emailExceptions = (socket.timeout, ConnectionError,
                       smtplib.SMTPAuthenticationError,
                       smtplib.SMTPConnectError,
                       smtplib.SMTPResponseException)

    if port == 25:
        try:
            with smtplib.SMTP(smtploc, port, timeout=10.) as server:
                retmsg = server.send_message(message)
            print("Email sent!")
            print("send_message returned:", retmsg)
            success = True
        except emailExceptions:
            print("Email sending failed! Bummer. Check SMTP setup!")
    elif port == 465:
        try:
            # NOTE: For this to work, you must ENABLE "Less secure app access"
            #   for Google/GMail/GSuite accounts! Otherwise you'll get
            # Return code 535
            # 5.7.8 Username and Password not accepted. Learn more at
            # 5.7.8  https://support.google.com/mail/?p=BadCredentials
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(smtploc, port,
                                  context=context, timeout=10.) as server:
                # Reminder: passw *MUST* be an ascii endoded string
                #   Sorry, no emoji passwords.
                server.login(user, passw)
                retmsg = server.send_message(message)
            print("Email sent!")
            success = True
        except emailExceptions as e:
            print(str(e))
            print("Email sending failed! Bummer. Check SMTP setup!")
    else:
        print("UNKNOWN SMTP METHOD! NOT SENDING ANY MAIL.")

    return success


def constructMail(subject, body, fromaddr, toaddr, fromname=None):
    """
    """
    msg = EmailMessage()
    if fromname is None:
        msg['From'] = fromaddr
    else:
        msg['From'] = "%s via <%s>" % (fromname, fromaddr)
    msg['To'] = toaddr

    # Make sure replies go to the list, not to this 'from' address
    msg.add_header('reply-to', toaddr)

    msg['Subject'] = subject
    msg.set_content(body)

    print(msg)

    return msg


def makeEmailUpdate(etype, jobid, jobname, strStat, emailConfig,
                    picam=None, ulticam=None):
    """
    """
    # First make sure we have at least a null string for the
    #   standard footer that is included with every email
    if emailConfig is not None:
        eFrom = emailConfig.fromname
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

        msg = constructMail(subject, body, eFrom, eTo)

        # Now grab and attach the images, if they were requested
        if ulticam is not None:
            # It's really just an http GET request so it's easy
            img = cameras.grab_ultimaker(ulticam.ip)
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
