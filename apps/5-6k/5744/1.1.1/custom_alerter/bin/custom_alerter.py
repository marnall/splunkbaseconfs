#! /usr/bin/python

import smtplib
import sys, os
import json
import logging
import logging.handlers
import urllib.parse
    
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import splunk.Intersplunk
import splunk.entity as entity
from splunk.rest import simpleRequest


def setup_logger(level):
    logger = logging.getLogger("custom_alerter_logger")
    logger.propagate = False
    logger.setLevel(level)
    file_handler = logging.handlers.RotatingFileHandler(os.environ['SPLUNK_HOME'] + '/var/log/splunk/custom_alerter.log', maxBytes=25000000, backupCount=5)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger

def getCredentials(sessionKey, namespace):
    try:
        uri = 'admin/alert_actions/email'
        response, content = simpleRequest(uri, method='POST', postargs={'show_password': True, 'output_mode': 'json'}, sessionKey=sessionKey)
        contentJson = json.loads(content)
        userCredentials = contentJson['entry'][0]['content']
        auth_username  = userCredentials.get('auth_username')
        clear_password = userCredentials.get('clear_password')
        mailserver = userCredentials.get('mailserver')
        fromUser = userCredentials.get('from')
        return auth_username, clear_password, mailserver, fromUser

    except Exception as e:
        logger.error("Could not retrieve splunk email setting. Error: %s" % (str(e)))

    return '', '', '', ''


def main():    
    try:    
        if len(sys.argv) > 1 and sys.argv[1] == "--execute":
            payload = json.loads(sys.stdin.read())
            
            logger.info(payload)
            configuration = payload.get('configuration')
            recipients = configuration.get('recipients')
            recipients_bcc = configuration.get('recipients_bcc')
            priority = configuration.get('priority')
            subject = configuration.get('subject')
            message = configuration.get('message')
            dashboard = configuration.get('dashboard')
            sessionKey = payload.get('session_key')
            
            if(recipients):            
                to = list(recipients.split(","))
            else:
                to = []
            
            if(recipients_bcc):
                to_bcc = list(recipients_bcc.split(","))
            else:
                to_bcc = []
                
            # Check if files are in local folder. If not use the default bin folder.
            if (os.path.isfile(os.environ['SPLUNK_HOME'] + '/etc/apps/custom_alerter/local/logo_base64.dat')):
                logo_path = os.environ['SPLUNK_HOME'] + "/etc/apps/custom_alerter/local/logo_base64.dat"
            else:
                logo_path = "logo_base64.dat"
            
            if (os.path.isfile(os.environ['SPLUNK_HOME'] + '/etc/apps/custom_alerter/local/footer.html')):
                footer_path = os.environ['SPLUNK_HOME'] + '/etc/apps/custom_alerter/local/footer.html'
            else:
                footer_path = "footer.html"
                
            if (os.path.isfile(os.environ['SPLUNK_HOME'] + '/etc/apps/custom_alerter/local/body.html')):
                body_path = os.environ['SPLUNK_HOME'] + '/etc/apps/custom_alerter/local/body.html'
            else:
                body_path = "body.html"
            
            if (os.path.isfile(os.environ['SPLUNK_HOME'] + '/etc/apps/custom_alerter/local/dashboardLink.html')):
                dashboardHTML_path = os.environ['SPLUNK_HOME'] + '/etc/apps/custom_alerter/local/dashboardLink.html'
            else:
                dashboardHTML_path = "dashboardLink.html"
            
            # load the body
            with open(body_path, 'r') as file:
                body = file.read().replace('\n', '')
            
            # load the logo
            with open(logo_path, 'r') as file:
                logo = file.read().replace('\n', '')
                
            # load the footer
            with open(footer_path, 'r') as file:
                footer = file.read().replace('\n', '')
                
            # load the dashboardlink button
            with open(dashboardHTML_path, 'r') as file:
                dashboardHTML = file.read().replace('\n', '')
            
            if (dashboard):
                dashboardHTML = dashboardHTML.replace('<<dashboard>>',dashboard)
                body = body.replace('<<dashboardHTML>>', dashboardHTML)
            else:
                body = body.replace('<<dashboard>>', '')
            
            body = body.replace('<<message>>', message)
            body = body.replace('<<footer>>', footer)
            body = body.replace('<<logo>>', logo)
            
            username, password, mailserver, fromUser = getCredentials(sessionKey, 'search')
            try:
                server, port = mailserver.split(':')
            except:
                server = mailserver
                port = ""

            sender = username
            # Create message container - the correct MIME type is multipart/alternative.
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = fromUser
            msg['To'] = ", ".join(to)
            msg['Bcc'] = ", ".join(to_bcc)
            msg['X-Priority'] = priority
            
            if (to) and (to_bcc):
                to = to + to_bcc
            else:
                if not (to) and (to_bcc):
                    to = to_bcc
                else:
                    if (to) and (not to_bcc):
                        to = to
            
            # Create the body of the message (a plain-text and an HTML version).
            text = message
            html = body
            
            # Record the MIME types of both parts - text/plain and text/html.
            part1 = MIMEText(text, 'plain')
            part2 = MIMEText(html, 'html')

            # Attach parts into message container.
            # According to RFC 2046, the last part of a multipart message, in this case
            # the HTML message, is best and preferred.
            msg.attach(part1)
            msg.attach(part2)

            # Send the message via local SMTP server.
            s = smtplib.SMTP(str(server), str(port))
            s.ehlo()
            if sender:
               s.starttls() #enable security
               s.login(sender, password)

            # sendmail function takes 3 arguments: sender's address, recipient's address
            # and message to send - here it is sent as one string.
            s.sendmail(fromUser, to, msg.as_string())
            s.quit()
   
    except Exception as e:
        logger.error("Error: %s" % (str(e)))

if __name__ == "__main__":
    logger = setup_logger(logging.INFO)
    main()
