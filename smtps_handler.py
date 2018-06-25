from session_manager import SessionManager

import logging.handlers
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.message import Message


class SMTPSHandler(logging.handlers.SMTPHandler):

    def emit(self, record):
        """
        Overwrite the logging.handlers.SMTPHandler.emit function with SMTP_SSL.
        Emit a record.
        Format the record and send it to the specified addressees.
        """
        try:
            import smtplib
            import ssl
            from email.utils import formatdate
            # context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
            port = self.mailport
            if not port:
                port = smtplib.SMTP_SSL_PORT
            smtp = smtplib.SMTP_SSL(self.mailhost, port, timeout=5)

            msg = MIMEMultipart()
            msg['Subject'] = self.getSubject(record)
            msg['From'] = self.fromaddr
            msg['To'] = self.toaddrs[0]
            msg['Date'] = formatdate()

            session = SessionManager()
            image_data = session.get_screenshot()
            text = MIMEText('Screenshot attached')
            msg.attach(text)
            image = MIMEImage(image_data, 'screenshot.png')
            msg.attach(image)

            if self.username:
                # smtp.ehlo()
                # smtp.starttls()  # for tls add this line context=context
                smtp.ehlo()
                smtp.login(self.username, self.password)
            smtp.sendmail(self.fromaddr, [self.toaddrs], msg.as_string())

            smtp.quit()
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)
