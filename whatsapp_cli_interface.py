import subprocess
import log_manager

logger = log_manager.get_logger('whatsapp_cli')


def send_whatsapp(number, message=None, media=None):
    logger.info('Whatsapp CLI interface started')

    process = "./venv/bin/python whatsapp_cli.py --numbers %s" % number

    if message:
        process += " --message \"%s\"" % message
    if media:
        process += " --media \"%s\"" % media

    logger.info('Process %s about to start' % process)

    if subprocess.call([process], shell=True):
        logger.info('Message sent')
        return True
    else:
        logger.error('Failed to send message')
        return False

    # try:
    #     subprocess.check_output([process], shell=True)
    #     logger.info('Message sent')
    #     return True
    #     # cli = whatsapp_cli.WhatsAppCli(session_manager.SessionManager)
    #     # if cli.send_message(number, message, media):
    #     #     logger.info('Message sent')
    #     #     return True
    #     # else:
    #     #     return False
    # except subprocess.CalledProcessError as e:
    #     logger.error('Failed to send message')
    #     return False
    # finally:
    #     logger.info('send_whatsapp complete')
