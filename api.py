from flask import Flask, request
from whatsapp.whatsapp_cli_interface import send_whatsapp
from logging_config import log_manager
import os
from elasticapm.contrib.flask import ElasticAPM
from elasticapm.handlers.logging import LoggingHandler
import logging
from flask_cors import CORS

from task_queue import tasks
from domain.delivery import Delivery

app = Flask(__name__)
CORS(app)

# Configure logging
if os.environ['ELASTIC_APM_SERVICE_NAME'] and os.environ['ELASTIC_APM_SERVER_URL']:
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

# Example usage:
# app.logger.error('Failed to send: Invalid number',
#                  exc_info=True,
#                  extra={
#                      'uid': uid
#                  })

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

    if send_whatsapp(Delivery(number=os.environ['CELL_NUMBER'], txt='Health check')):
        return 'healthy', 200
    else:
        return 'unhealthy', 500


@app.route('/purge_tasks')
def purge_tasks():
    if not check_auth():
        return 'unauthorized', 400
    else:
        pass

    logger.info('Handling /handle_schedules request')

    tasks_purged = tasks.purge_tasks()

    return '%s tasks purged' % tasks_purged


@app.route('/handle_schedules')
def handle_schedules():
    if not check_auth():
        return 'unauthorized', 400
    else:
        pass

    logger.info('Handling /handle_schedules request')

    from schedule_manager import ScheduleManager
    ScheduleManager().handle_schedules()

    return 'Process started'


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

    message = Delivery(number=number, txt=txt, url=url, media=media, filename=filename)

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

    if tasks.queue_send_broadcast(receivers, Delivery(txt=txt, url=url, media=media, filename=filename)):
        return 'Broadcast started'


def check_auth():
    return request.headers.get('X-Auth-Token') == os.environ['API_AUTH_TOKEN']


def start():
    try:
        app.run(host='0.0.0.0', port='8001', use_reloader=False)
    except OSError:
        logger.error('Address already in use')
        pass
