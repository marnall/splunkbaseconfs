# coding: utf-8
from __future__ import print_function
import sys
import os
import datetime
import json
import re
from mako import template

import base64
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage

import splunk.entity as entity
import splunk.search as search
from splunk.rest import simpleRequest
import splunk.secure_smtplib as secure_smtplib
import splunk.ssl_context as ssl_context

EMAIL_DELIM = re.compile('\s*[,;]\s*')
CHARSET = "UTF-8"
RESULT_TABLE = re.compile('<table id="result_table"></table>')

def htmlTableTemplate():
    return template.Template('''
% if len(results) > 0:
<table class="row" style="border-collapse:collapse;border-spacing:0;display:table;padding:0;position:relative;text-align:left;vertical-align:top;width:100%">
    <tbody>
         <tr style="padding:0;text-align:left;vertical-align:top">
            <th class="small-12 large-8 columns first last" style="Margin:0 auto;color:#0a0a0a;font-family:Helvetica,Arial,sans-serif;font-size:16px;font-weight:400;line-height:1.3;margin:0 auto;padding:0;padding-bottom:16px;padding-left:16px;padding-right:16px;text-align:left;width:370.67px">
                 <table class="results" style="border-collapse:collapse;border-spacing:0;margin:0;padding:0;text-align:left;vertical-align:top;width:100%" border="0" cellpadding="0" cellspacing="0">
                    <tbody>
                        <% cols = [] %>
                        <tr style="padding:0;text-align:left;vertical-align:top">
                            % for key in fields:
                            % if not key.startswith("_") or key == "_raw" or key == "_time":
                            <% cols.append(key) %>
                            <th class="text-center" style="Margin:0;border-bottom:1px dotted #ccc;color:#0a0a0a;font-family:Helvetica,Arial,sans-serif;font-size:12px;font-weight:bold;line-height:1.3;margin:0;padding:0;text-align:center;white-space:nowrap;overflow: hidden;word-break: keep-all">${key}</th>
                            % endif
                            % endfor
                        </tr>
                        % for result in results:
                        <tr style="padding:0;text-align:left;vertical-align:top">
                            % for col in cols:
                            <td class="text-center" style="-moz-hyphens:auto;-webkit-hyphens:auto;Margin:0;border-bottom:1px dotted #ccc;border-collapse:collapse!important;color:#0a0a0a;font-family:Helvetica,Arial,sans-serif;font-size:12px;font-weight:400;hyphens:auto;line-height:1.3;margin:0;padding:0;text-align:center;vertical-align:top;word-wrap:break-word">
                            % if isinstance(result.get(col), list):
                                % for val in result.get(col):
                                    ${val}
                                % endfor
                            % else:
                                ${result.get(col)}
                            % endif
                            </td>
                            % endfor
                        </tr>
                        % endfor
                    </tbody>
                  </table>
            </th>
         </tr>
    </tbody>
</table>
% endif
''')

def unquote(val):
    if val is not None and len(val) > 1 and val.startswith(
            '"') and val.endswith('"'):
        return val[1:-1]
    return val

def log(msg):
    with open(os.path.join(
            os.environ["SPLUNK_HOME"], "var", "log", "splunk",
            "test_email.log"), "a") as f:
        print(str(datetime.datetime.now().isoformat()), msg, file=f)

def send_email(configuration_settings, global_email_settings):
    username = global_email_settings.get('auth_username')
    password = global_email_settings.get('auth_password')
    smtpserver = global_email_settings.get('mailserver')
    session_key = configuration_settings['session_key']
    sid = configuration_settings['job_id']
    expected_fields=[]
    if configuration_settings.get('fields'):
        expected_fields = EMAIL_DELIM.split(configuration_settings.get('fields'))
        results = get_results(session_key, sid, expected_fields)

    html_value = configuration_settings.get('message')

    def has_id(id):
        if html_value and html_value.find("cid:" + id) != -1:
            return True
        else:
            return False

    def replace_images_with_cid_paths(body_html):
        """Parse the message HTML and identify images"""
        html_filter = body_html
        if body_html:
            matches = re.findall(r'\ssrc="([^"]+)"', body_html)
            image_counter = 1
            cid_images = []
            for image in matches:
                cid_id = "image_%s" % (image_counter)
                image_counter = image_counter + 1
                original_image_src = image

                cid_images.append({
                    'src': original_image_src,
                    'cid_id': cid_id
                })
                html_filter = html_filter.replace(image, "cid:%s"%cid_id)

            return (html_filter, cid_images)
        else:
            return (body_html, [])

    def normalize_image_url(url):

        if '//' not in url.lower():
            url = u"%s" % (url)

        return url

    def convert_image_to_cid(image_src):
        """Turn image path into a MIMEImage"""
        cid_id = image_src['cid_id']
        try:

            if 'data:image/png;base64,' in image_src['src'].lower():
                mime_image = MIMEImage(base64.b64decode(image_src['src'].split(',')[1]))
            else:

                raise Exception('only accept png format')

            # Define the image's ID as referenced above
            mime_image.add_header('Content-ID', '<%s>' % (cid_id))
            msg_root.attach(mime_image)

        except Exception as e:
            log(u"ERROR creating mime_image %s" % (str(e)))
            return None

    def add_image(name, to_add):
        if to_add:
            file_path = os.path.join(
                os.environ["SPLUNK_HOME"], "etc", "apps", "ARTs", "appserver",
                "static", "images", "email", name)
            fp = None
            try:
                fp = open(file_path)
                data = fp.read()
                msgImage = MIMEImage(data)
                msgImage.add_header(
                    'Content-ID', '<' + name.split(".")[0] + '>')
                msg_root.attach(msgImage)

            except Exception as ex:
                log('[read img error] file:' + name)
                log('[read img error] exception:' + str(ex))
            finally:
                if fp is not None:
                    fp.close()


    sender = 'ARTs-no-reply@splunk.com'

    recipients = []

    # Set the root information
    msg_root = MIMEMultipart('related')
    msg_root['From'] = sender

    if configuration_settings.get('to'):
        to = configuration_settings.get('to')
        recipients.extend(EMAIL_DELIM.split(to))
        msg_root['To'] = ','.join(EMAIL_DELIM.split(to))

    if configuration_settings.get('cc'):
        cc = configuration_settings.get('cc')
        recipients.extend(EMAIL_DELIM.split(cc))
        msg_root['Cc'] = ','.join(EMAIL_DELIM.split(cc))

    if configuration_settings.get('bcc'):
        bcc = configuration_settings.get('bcc')
        recipients.extend(EMAIL_DELIM.split(bcc))
        msg_root['Bcc'] = ','.join(EMAIL_DELIM.split(bcc))

    if configuration_settings.get('subject'):
        subject = configuration_settings.get('subject')
        msg_root['Subject'] = subject

    # username = ''
    # password = ''

    # Set the message content
    # msg_txt = MIMEText(configuration_settings.get('message'), 'html', 'utf-8')

    if len(expected_fields) > 0:
        table_html=htmlTableTemplate().render(
            results=results, fields=expected_fields)
        html_value = RESULT_TABLE.sub(table_html, html_value)


    message_with_images_prepared, cid_images = replace_images_with_cid_paths(
        html_value)
    msgText = MIMEText(message_with_images_prepared,
                       "html",'utf-8')
    msg_root.attach(msgText)

    for image in cid_images:
        convert_image_to_cid(image)

    add_image("firefox.png", has_id('firefox'))
    add_image("linux.png", has_id('linux'))
    add_image("ie11.png", has_id('ie11'))
    add_image("win10.png", has_id('win10'))
    add_image("chrome.png", has_id('chrome'))


    log('server:'+smtpserver)
    log('to'+configuration_settings.get('to'))

    if smtpserver and configuration_settings.get('to'):

        try:
            # setup the Open SSL Context
            sslHelper = ssl_context.SSLHelper()

            # current
            serverConfJSON = sslHelper.getServerSettings(session_key)
            # #Pass in settings from alert_actions.conf into context
            ctx = sslHelper.createSSLContextFromSettings(
                sslConfJSON=getAlertActions(session_key),
                serverConfJSON=serverConfJSON,
                isClientContext=True)

            # jackhammer
            # ctx = sslHelper.createSSLContextFromSettings(
            #     confJSON=getAlertActions(session_key),
            #     sessionKey=session_key,
            #     isClientContext=True)

            # send the mail
            if not global_email_settings['use_ssl']:
                smtp = secure_smtplib.SecureSMTP(host=smtpserver)
            else:
                smtp = secure_smtplib.SecureSMTP_SSL(
                    host=smtpserver, sslContext=ctx)

            # smtp.set_debuglevel(1)

            if global_email_settings['use_tls']:
                smtp.starttls(ctx)
            if len(username) > 0 and password is not None and len(password) > 0:
                smtp.login(username, password)
            log('[connect!]')
            smtp = smtplib.SMTP()
            smtp.connect(smtpserver)
            smtp.sendmail(sender, recipients, msg_root.as_string())
            smtp.quit()
            log('[done!]')
        except Exception as ex:
            log("[error:]" + str(ex))
    else:
        log('[error]missing info!')

def get_email_settings(session_key):
    emailInfo = entity.buildEndpoint(
        ['alerts', 'alert_actions', 'email'],
        namespace="system", owner="nobody")
    emailInfoHeader, emailInfoBoby = simpleRequest(
        emailInfo, method='GET', getargs={'output_mode': 'json'},
        sessionKey=session_key)
    return json.loads(emailInfoBoby)['entry'][0]['content']

def getAlertActions(sessionKey):
    settings = None
    try:
        settings = entity.getEntity(
            '/configs/conf-alert_actions',
            'email', namespace='system', owner='nobody', sessionKey=sessionKey)

        # log("[info]sendemail.getAlertActions conf file settings %s" % settings)
    except Exception as e:
        log(
            "[error]Could not access or parse email stanza of alert_actions.conf. Error=%s" % str(
                e))

    return settings

def get_results(sessionKey, job_id, expected_fields):
    job = search.getJob(job_id, sessionKey=sessionKey)
    resultset = list(job)
    output = []
    for result in resultset:
        temp = {}
        for field in expected_fields:
            temp[field] = result.fields[field]
        output.append(temp)
    return output

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == "--execute":
        payload = json.loads(sys.stdin.read())
        log("-" * 50)
        log("Log for alert [" + payload['search_name'] + "]")
        global_email_settings = get_email_settings(payload['session_key'])

        configuration_settings = payload.get('configuration')
        configuration_settings['session_key'] = payload['session_key']
        configuration_settings['job_id'] = payload['sid']

        send_email(configuration_settings, global_email_settings)

    else:
        print("invalid execution mode (expected --execute flag)", file=sys.stderr)
        sys.exit(1)