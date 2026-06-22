import smtplib

sender = "splunk@cyberfoxglobal.com"
recipient = "a.tungatov@cyberfoxglobal.com"
message = "Subject: test\n\nThis is test."

smtp=smtplib.SMTP("mail.cyberfoxglobal.com",25)
smtp.starttls()
smtp.sendmail(sender, recipient, message)
smtp.quit()

