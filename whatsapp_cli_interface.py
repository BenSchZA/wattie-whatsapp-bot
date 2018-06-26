import subprocess
import log_manager

logger = log_manager.get_logger('whatsapp_cli')


def send_whatsapp(number, message=None, media=None):
    logger.info('Whatsapp CLI interface started')

    process = "python whatsapp_cli.py --numbers %s" % number

    if message:
        process += " --message \"%s\"" % message
    if media:
        process += " --media \"%s\"" % media

    logger.info('Process %s about to start' % process)

    try:
        subprocess.check_output([process], shell=True)
        logger.info('Message sent')
        return True
    except subprocess.CalledProcessError as e:
        logger.error('Failed to send message: %s' % e.output)
        return False
    finally:
        logger.info('send_whatsapp complete')
