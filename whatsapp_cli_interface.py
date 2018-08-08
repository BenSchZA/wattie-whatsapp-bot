import subprocess
import log_manager
from message import Message

logger = log_manager.get_logger('whatsapp_cli')


def send_whatsapp(message: Message):
    logger.info('Whatsapp CLI interface started')

    if not message.number:
        logger.error('Failed to send message: Invalid number')
        return False

    process = "python whatsapp_cli.py --number %s" % message.number

    if message.url and message.txt:
        # process += " --url \"%s\"" % url
        message.txt = "%s\n%s" % (message.txt, message.url)
    if message.url and not message.txt:
        process += " --url \"%s\"" % message.url
    if message.txt:
        process += " --txt \"%s\"" % message.txt
    if message.media:
        process += " --media \"%s\"" % message.media

    logger.info('Process %s about to start' % process)

    try:
        stdout = subprocess.check_output([process], shell=True).decode()
        logger.info('Message sent')
        logger.debug(stdout)
        return True
    except subprocess.CalledProcessError as e:
        logger.error('Failed to send message: %s' % e.output)
        return False
    finally:
        logger.info('send_whatsapp complete')
