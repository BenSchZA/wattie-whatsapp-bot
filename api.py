from flask import Flask, request
from whatsapp_cli_interface import send_whatsapp
from file_manager import FileManager
import log_manager
import os
from elasticapm.contrib.flask import ElasticAPM
from elasticapm.handlers.logging import LoggingHandler
import logging
from schedule_manager import ScheduleManager
from flask_admin import Admin

app = Flask(__name__)

# configure to use ELASTIC_APM in your application's settings from elasticapm.contrib.flask import ElasticAPM
app.config['ELASTIC_APM'] = {
    # allowed app_name chars: a-z, A-Z, 0-9, -, _, and space from elasticapm.contrib.flask
    'APP_NAME': os.environ['ELASTIC_APM_SERVICE_NAME'],
    # 'SECRET_TOKEN': 'yourToken', #if you set on the APM server configuration
    'SERVER_URL': os.environ['ELASTIC_APM_SERVER_URL']  # your APM server url
}

apm = ElasticAPM(app)

handler = LoggingHandler(client=apm.client)
handler.setLevel(logging.WARN)
app.logger.addHandler(handler)

logger = log_manager.get_logger('api_manager')
schedule_manager = ScheduleManager()


@app.route("/ping")
def ping():
    return 'healthy', 200


@app.route("/health")
def health_check():
    if not check_auth():
        return 'unauthorized', 400
    else:
        pass

    logger.info('Handling /health request')

    if send_whatsapp(number=os.environ['CELL_NUMBER'], message='Health check'):
        return 'healthy', 200
    else:
        return 'unhealthy', 500


@app.route('/handle_schedules')
def handle_schedules():
    # if not check_auth():
    #     return 'unauthorized', 400
    # else:
    #     pass

    logger.info('Handling /handle_schedules request')

    schedule_manager.handle_schedules()

    return 'Process started'


@app.route('/message')
def send_message():
    if not check_auth():
        return 'unauthorized', 400
    else:
        pass

    logger.info('Handling /message request: %s' % request.args)

    number = request.args.get('number')
    message = request.args.get('message')
    media = request.args.get('media')
    filename = request.args.get('filename')
    url = request.args.get('url')

    file_manager = FileManager()
    path = ''

    if not number:
        return

    if media and filename:
        logger.info('Fetching media')
        file_manager = FileManager()
        path = file_manager.download_temp_file(media, filename)
    elif media and not filename:
        return '"media" must have corresponding "filename"'

    if message and not media:
        logger.info('Sending message')
        if send_whatsapp(number=number, message=message):
            return 'Message \"%s\" sent to %s' % (message, number)
        else:
            return 'Failed to send message'
    elif message and media:
        logger.info('Sending media message')
        if send_whatsapp(number=number, message=message, media=path):
            file_manager.delete_temp_files()
            return 'Message \"%s\" sent to %s with attachment %s' % (message, number, media)
        else:
            return 'Failed to send message'
    elif not message and media:
        logger.info('Sending media')
        if send_whatsapp(number=number, media=path):
            file_manager.delete_temp_files()
            return 'Message sent to %s with attachment %s' % (number, media)
        else:
            return 'Failed to send message'
    return 'Invalid request', 400


@app.route('/***REMOVED***')
def send_***REMOVED***():
    uid = request.args.get('uid')

    if not check_auth():
        app.logger.error('Failed to send ***REMOVED***: Unauthorized',
                         exc_info=True,
                         extra={
                             'uid': uid
                         })
        return 'unauthorized', 400
    else:
        pass

    logger.info('Handling /***REMOVED*** request: %s' % request.args)

    uid = request.args.get('uid')
    number = request.args.get('number')
    message = request.args.get('message')
    media = request.args.get('media')
    url = request.args.get('url')

    if not number:
        app.logger.error('Failed to send ***REMOVED***: Invalid number',
                         exc_info=True,
                         extra={
                             'uid': uid
                         })
        return 'Invalid "number"', 400

    if send_whatsapp(number=number, message=message, media=media, url=url):
        return 'Message sent to %s' % number, 200
    else:
        app.logger.error('Failed to send ***REMOVED***',
                         exc_info=True,
                         extra={
                             'uid': uid,
                             'number': number,
                             'text': message,
                             'media': media,
                             'url': url
                         })
        return 'Failed to send message', 400


def check_auth():
    return request.headers.get('X-Auth-Token') == os.environ['AUTH_TOKEN']


def start():
    try:
        app.run(host='0.0.0.0', port='8001', use_reloader=False)
    except OSError:
        logger.error('Address already in use')
        pass
