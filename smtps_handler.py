import logging.handlers


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
            msg = self.format(record)
            msg = "From: %s\r\nTo: %s\r\nSubject: %s\r\nDate: %s\r\n\r\n%s" % (self.fromaddr, ", ".join(self.toaddrs), self.getSubject(record), formatdate(), msg)
            if self.username:
                # smtp.ehlo()
                # smtp.starttls()  # for tls add this line context=context
                smtp.ehlo()
                smtp.login(self.username, self.password)
            smtp.sendmail(self.fromaddr, self.toaddrs, msg)
            smtp.quit()
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)
