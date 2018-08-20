from pymongo.collection import ObjectId
import os
import requests
import jsonpickle

import log_manager
from file_manager import FileManager
from user import User
from schedule import Schedule
from message import Message
from whatsapp_cli_interface import send_whatsapp
from alert_manager import AlertManager
from whatsapp_process import WhatsAppProcess

from kombu import Queue
from celery import Celery
from celery import group
from celery.exceptions import SoftTimeLimitExceeded
from celery.exceptions import MaxRetriesExceededError

from elasticapm import Client

client = Client({'SERVICE_NAME': os.environ['ELASTIC_APM_SERVICE_NAME'],
                 'SERVER_URL': os.environ['ELASTIC_APM_SERVER_URL']})

app = Celery('tasks', broker='redis://redis')

app.conf.task_queues = (
    Queue('download'),
    Queue('deliver'),
    Queue('send_message'),
    Queue('process_message')
)

whatsapp_process = WhatsAppProcess()
file_manager = FileManager()
alert_manager = AlertManager()
logger = log_manager.get_logger('session_manager')


def purge_tasks():
    app.control.purge()


def queue_download_and_deliver(user: User):
    user_json = jsonpickle.dumps(user)
    download_and_deliver.apply_async(args=[user_json], queue='download')


def queue_send_message(message: Message):
    message_json = jsonpickle.dumps(message)
    send_message.apply_async(args=[message_json], queue='send_message')


def queue_send_broadcast(receivers, message: Message):
    return group(send_message.s(jsonpickle.dumps(message.set_number(number))) for number in receivers) \
        .apply_async(queue='send_message')


def queue_process_new_users():
    return process_new_users.apply_async(queue='process_message', task_id='unique_process-new-users')


@app.task(bind=True)
def process_new_users(self):
    whatsapp_process.process_new_users()


@app.task(bind=True, soft_time_limit=30, default_retry_delay=5, max_retries=5)
def send_message(self, message: Message):
    client.begin_transaction('send_message')
    try:
        message: Message = jsonpickle.loads(message, classes=[Message])

        if message.media and message.filename:
            logger.info('Fetching media')
            path = file_manager.download_temp_file(message.media, message.filename)
            message.media = path
        elif message.media and not message.filename:
            raise ValueError('"media" must have corresponding "filename"')

        if send_whatsapp(message):
            if message.media:
                file_manager.delete_temp_files()
            logger.info('Message \"%s\" sent to %s' % (message.__dict__, message.number))
        else:
            logger.error('Failed to send message', 400)
            raise ValueError('Failed to send message')

        client.end_transaction('send_message')
        return message
    except (ValueError, SoftTimeLimitExceeded) as e:
        client.end_transaction('send_message')
        client.capture_exception()
        self.retry(exc=e)
        alert_manager.slack_alert('***REMOVED*** ***REMOVED*** Failed to send message to number %s with txt: %s'
                                  % (message.number, message.txt))

# @app.task(bind=True, soft_time_limit=30, default_retry_delay=5, max_retries=5)
# def download_media(self, message: Message):


@app.task(bind=True, soft_time_limit=30, default_retry_delay=5, max_retries=5)
def download_and_deliver(self, user):
    try:
        user: User = jsonpickle.loads(user, classes=[User, User.***REMOVED***, Schedule])

        # Clear user db entry and downloads
        file_manager.remove_schedule(user.uid)
        if file_manager.does_path_exist(file_manager.get_user_download_path(user.uid)):
            file_manager.delete_user_file(user.uid)

        path = ''
        if user.deliver_voicenote:
            path = file_manager.download_user_file(user)

        # Update/create database entry for logging and management
        logger.debug('Scheduled time: %s' % user.***REMOVED***.scheduled_date)

        schedule_id = file_manager.create_db_schedule(user, path)

        schedule = file_manager.downloads_collection.find_one({"_id": ObjectId(schedule_id)})
        schedule = Schedule(user, schedule['path'])

        user_json = jsonpickle.dumps(user)
        schedule_json = jsonpickle.dumps(schedule)
        deliver.apply_async(args=[user_json, schedule_json], queue='deliver')

        return user, schedule
    except SoftTimeLimitExceeded as e:
        self.retry(exc=e)


@app.task(bind=True, soft_time_limit=30, default_retry_delay=5, max_retries=5)
def deliver(self, user, schedule):
    user: User = jsonpickle.loads(user, classes=[User, User.***REMOVED***, Schedule])
    user_json = jsonpickle.dumps(user)
    schedule = jsonpickle.loads(schedule, classes=[User, User.***REMOVED***, Schedule])

    try:
        if user.deliver_voicenote and not file_manager.does_path_exist(file_manager.get_user_download_path(user.uid)):
            download_and_deliver.apply_async(args=[user_json], queue='download')
            raise Exception('User download not available')

        # If schedule delivered successfully, delete user file and mark delivered, else clear schedule
        if _deliver_schedule(schedule):
            file_manager.delete_user_file(user.uid)
            file_manager.mark_delivered(schedule)
            user.***REMOVED***.delivered = True
            return True
        else:
            user.***REMOVED***.delivered = False
            self.retry(exc=Exception('Delivery failed'))
            alert_manager.slack_alert('***REMOVED*** ***REMOVED*** Failed to deliver ***REMOVED*** to user %s with schedule: %s'
                                      % (user.uid, str(schedule.__dict__)))

    except Exception as exc:
        if isinstance(exc, SoftTimeLimitExceeded):
            try:
                self.retry(exc=exc)
            except MaxRetriesExceededError:
                logger.error('Max retries exceeded')
                file_manager.delete_user_file(user.uid)
                file_manager.remove_schedule(user.uid)
                download_and_deliver.apply_async(args=[user_json], queue='download')
                alert_manager.slack_alert('***REMOVED*** ***REMOVED*** Failed to deliver ***REMOVED*** to user %s with schedule: %s'
                                          % (user.uid, str(schedule.__dict__)))
        else:
            alert_manager.slack_alert('***REMOVED*** ***REMOVED*** Failed to deliver ***REMOVED*** to user %s with schedule: %s'
                                      % (user.uid, str(schedule.__dict__)))
            raise exc


def _deliver_schedule(schedule: Schedule):
    logger.info("Delivering message to %s " % schedule.uid)
    logger.debug("Schedule entry: %s" % schedule)

    deliver_voicenote = schedule.deliver_voicenote
    deliver_weblink = schedule.deliver_weblink

    uid = schedule.uid
    number = schedule.number
    media = None
    url = None

    if deliver_voicenote and deliver_weblink:
        message = "Hello %s! Here\'s your personalized ***REMOVED***:" % schedule.name
        media = schedule.path
        url = "https://my***REMOVED***.com/***REMOVED***/%s" % schedule.***REMOVED***_token
    elif deliver_voicenote and not deliver_weblink:
        message = "Hello %s! Here\'s your personalized ***REMOVED***:" % schedule.name
        media = schedule.path
    elif not deliver_voicenote and deliver_weblink:
        message = "Hello %s! Here\'s your personalized ***REMOVED***:" % schedule.name
        url = "https://my***REMOVED***.com/***REMOVED***/%s" % schedule.***REMOVED***_token
    else:
        logger.error('***REMOVED*** failed to deliver to %s' % uid)
        alert_manager.slack_alert('***REMOVED*** ***REMOVED*** Failed to deliver ***REMOVED*** to user %s with schedule: %s'
                                  % (uid, str(schedule.__dict__)))
        return False

    params = {
        'uid': uid,
        'number': number,
        'txt': message,
        'media': media,
        'url': url
    }

    headers = {
        'X-Auth-Token': os.environ['AUTH_TOKEN']
    }

    req = requests.get("http://0.0.0.0:8001/***REMOVED***", params=params, headers=headers)

    if req.status_code == 200:
        logger.info('***REMOVED*** delivered to %s' % uid)
        logger.debug('%s %s' % (req.status_code, req.reason))
        return True
    else:
        logger.error('***REMOVED*** failed to deliver to %s' % uid)
        logger.debug('%s %s' % (req.status_code, req.reason))
        alert_manager.slack_alert('***REMOVED*** ***REMOVED*** Failed to deliver ***REMOVED*** to user %s with schedule: %s'
                                  % (uid, str(schedule.__dict__)))
        return False
