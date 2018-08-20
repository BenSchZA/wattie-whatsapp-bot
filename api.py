from flask import Flask, request
from whatsapp_cli_interface import send_whatsapp
import log_manager
import os
from elasticapm.contrib.flask import ElasticAPM
from elasticapm.handlers.logging import LoggingHandler
import logging
from schedule_manager import ScheduleManager
from flask_cors import CORS

import tasks
from message import Message

app = Flask(__name__)
CORS(app)

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

    if send_whatsapp(Message(number=os.environ['CELL_NUMBER'], txt='Health check')):
        return 'healthy', 200
    else:
        return 'unhealthy', 500


@app.route('/handle_schedules')
def handle_schedules():
    if not check_auth():
        return 'unauthorized', 400
    else:
        pass

    logger.info('Handling /handle_schedules request')

    schedule_manager.handle_schedules()

    return 'Process started'


@app.route('/process_new_users')
def process_new_users():
    if not check_auth():
        return 'unauthorized', 400
    else:
        pass

    logger.info('Handling /process_new_users request')

    if tasks.queue_process_new_users():
        return 'Process started'
    else:
        return 'Process failed', 400


@app.route('/message')
def send_message():
    if not check_auth():
        return 'unauthorized', 400
    else:
        pass

    logger.info('Handling /message request: %s' % request.values)

    number = request.args.get('number')
    txt = request.args.get('txt')
    url = request.args.get('url')
    media = request.args.get('media')
    filename = request.args.get('filename')

    if not number:
        return 'Invalid "number"', 400

    message = Message(number, txt, url, media, filename)

    if tasks.queue_send_message(message):
        return 'Message \"%s\" for %s added to queue' % (txt, number)
    else:
        return 'Invalid request', 400


@app.route('/broadcast', methods=['POST'])
def send_broadcast():
    if not check_auth():
        return 'unauthorized', 400
    else:
        pass

    logger.info('Handling /broadcast request: %s' % request.get_json())
    logging.debug('Headers: %s' % request.headers.__dict__)

    request_body = request.get_json()

    receivers = request.get_json().get('receivers')

    txt = request_body.get('txt')
    url = request_body.get('url')
    media = request_body.get('media')
    filename = request_body.get('filename')

    if not receivers:
        return 'Invalid "receivers"', 400
    if not txt:
        return 'Invalid "txt"', 400

    if tasks.queue_send_broadcast(receivers, Message(txt=txt, url=url, media=media, filename=filename)):
        return 'Broadcast started'


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

    logger.info('Handling /***REMOVED*** request: %s' % request.values)

    uid = request.args.get('uid')
    number = request.args.get('number')
    txt = request.args.get('txt')
    media = request.args.get('media')
    url = request.args.get('url')

    if not number:
        app.logger.error('Failed to send ***REMOVED***: Invalid number',
                         exc_info=True,
                         extra={
                             'uid': uid
                         })
        return 'Invalid "number"', 400

    if send_whatsapp(Message(number=number, txt=txt, media=media, url=url)):
        return 'Message sent to %s' % number, 200
    else:
        app.logger.error('Failed to send ***REMOVED***',
                         exc_info=True,
                         extra={
                             'uid': uid,
                             'number': number,
                             'text': txt,
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
