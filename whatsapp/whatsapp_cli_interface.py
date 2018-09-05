import subprocess
from logging_config import log_manager
from domain.delivery import Delivery

logger = log_manager.get_logger('whatsapp_cli')


def send_whatsapp(delivery: Delivery):
    logger.info('Whatsapp CLI interface started')

    if not delivery.number:
        logger.error('Failed to send message: Invalid number')
        return False

    process = "python whatsapp/whatsapp_cli.py --number %s" % delivery.number

    if delivery.url:
        process += " --url \"%s\"" % delivery.url
    if delivery.txt:
        process += " --txt \"%s\"" % delivery.txt
    if delivery.media:
        process += " --media \"%s\"" % delivery.media

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
