#!/usr/bin/env python
from __future__ import print_function
import smtplib
from email.MIMEMultipart import MIMEMultipart
from email.MIMEBase import MIMEBase
from email.MIMEText import MIMEText
from email.Utils import COMMASPACE, formatdate
from email import Encoders
import os
import sys


def checkPasswd(server, ssl_port=465, ssl_username='', ssl_passwd=''):
    try:
        smtp = smtplib.SMTP_SSL(server, port=ssl_port)
        smtp.login(ssl_username, ssl_passwd)
        smtp.close()
    except smtplib.SMTPAuthenticationError:
        return False
    return True


def sendMail(to, subject, text, files=[], server="mail1.psfc.mit.edu",
             ssl=False, ssl_port=465, ssl_username='', ssl_passwd=''):
    assert type(to) == list
    assert type(files) == list
#    me =  'shiraiwa@psfc.mit.edu'
    me = ssl_username  # 'shiraiwa@psfc.mit.edu'
    msg = MIMEMultipart()
    msg['From'] = me
#    msg['To'] = COMMASPACE.join(['shiraiwa@psfc.mit.edu'])
    msg['To'] = COMMASPACE.join(to)
    msg['Date'] = formatdate(localtime=True)
    msg['Subject'] = subject

    msg.attach(MIMEText(text))

    for file in files:
        part = MIMEBase('application', "octet-stream")
        part.set_payload(open(file, "rb").read())
        Encoders.encode_base64(part)
        part.add_header('Content-Disposition', 'attachment; filename="%s"'
                        % os.path.basename(file))
        msg.attach(part)

    if ssl:
        print((server, ssl_port))
        smtp = smtplib.SMTP_SSL(server, ssl_port)
        smtp.login(ssl_username, ssl_passwd)
    else:
        smtp = smtplib.SMTP(server)
    smtp.sendmail(me, to, msg.as_string())
    smtp.close()


if __name__ == '__main__':
    if len(sys.argv[1:]) == 1:
        file = sys.argv[1:][0]
        if os.path.exists(file):
            print('sending : '+file)
            file = os.path.abspath(file)
        sendMail(
            ["shiraiwa@psfc.mit.edu"],
            "mail attachement", "attached!\n",
            [file]
        )
