from flask import Flask, request
from whatsapp_cli_interface import send_whatsapp
from file_manager import FileManager
import log_manager
import os
from elasticapm.contrib.flask import ElasticAPM

app = Flask(__name__)

# configure to use ELASTIC_APM in your application's settings from elasticapm.contrib.flask import ElasticAPM
app.config['ELASTIC_APM'] = {
    # allowed app_name chars: a-z, A-Z, 0-9, -, _, and space from elasticapm.contrib.flask
    'APP_NAME': os.environ['ELASTIC_APM_SERVICE_NAME'],
    # 'SECRET_TOKEN': 'yourToken', #if you set on the APM server configuration
    'SERVER_URL': os.environ['ELASTIC_APM_SERVER_URL']  # your APM server url
}

apm = ElasticAPM(app)

logger = log_manager.get_logger('api_manager')


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
    if not check_auth():
        return 'unauthorized', 400
    else:
        pass

    logger.info('Handling /***REMOVED*** request: %s' % request.args)

    number = request.args.get('number')
    message = request.args.get('message')
    media = request.args.get('media')
    url = request.args.get('url')

    if not number:
        return 'Invalid "number"', 400

    if send_whatsapp(number=number, message=message, media=media, url=url):
        return 'Message sent to %s' % number, 200
    else:
        return 'Failed to send message', 400


def check_auth():
    return request.headers.get('X-Auth-Token') == os.environ['AUTH_TOKEN']


def start():
    try:
        app.run(host='0.0.0.0', port='8001', use_reloader=False)
    except OSError:
        logger.error('Address already in use')
        pass
