from pymongo.collection import ObjectId
import requests
import jsonpickle

from logging_config import log_manager
from file_manager import FileManager
from domain.user import User
from domain.schedule import Schedule
from domain.delivery import Delivery
from whatsapp.whatsapp_cli_interface import send_whatsapp
from alert_manager import AlertManager
from whatsapp.whatsapp_process import WhatsAppProcess

from celery.signals import task_postrun
from celery import group
from celery.exceptions import SoftTimeLimitExceeded
from celery.exceptions import MaxRetriesExceededError

from elasticapm import Client

from task_queue.celery_config import *

client = Client({'SERVICE_NAME': os.environ['ELASTIC_APM_SERVICE_NAME'],
                 'SERVER_URL': os.environ['ELASTIC_APM_SERVER_URL']})

file_manager = FileManager()
alert_manager = AlertManager()
logger = log_manager.get_logger('session_manager')


def purge_tasks():
    """
    Clear all tasks from queues
    :returns number of tasks purged
    """
    return app.control.purge()


def task_in_queue(check_id, queue_id):
    """
    Inspect queue to check for ID: reserved, active, or scheduled
    :returns true if task in queue
    """
    inspect = app.control.inspect([queue_id])

    reserved = inspect.reserved()
    active = inspect.active()
    scheduled = inspect.scheduled()

    logger.info('Reserved %s' % reserved)
    logger.info('Active %s' % active)
    logger.info('Scheduled %s' % scheduled)

    if reserved or active or scheduled:
        tasks = list(map(lambda x: x.get('id'), reserved.get(queue_id))) \
            + list(map(lambda x: x.get('id'), active.get(queue_id))) \
            + list(map(lambda x: x.get('id'), scheduled.get(queue_id)))
    else:
        tasks = []
    logger.info('Tasks %s' % tasks)

    return any(task_id == check_id for task_id in tasks)


def queue_download_and_deliver(user: User):
    user_json = jsonpickle.dumps(user)
    return download_and_deliver.apply_async(args=[user_json], queue='download')


def queue_send_message(delivery: Delivery):
    message_json = jsonpickle.dumps(delivery)
    return send_message.apply_async(args=[message_json], queue='send_message')


def queue_send_broadcast(receivers, delivery: Delivery):
    return group(send_message.s(jsonpickle.dumps(delivery.set_number(number))) for number in receivers) \
        .apply_async(queue='send_message')


def queue_process_new_users():
    task_id = 'unique_process-new-users'
    if task_in_queue(task_id, 'celery@worker_q_selenium'):
        logger.info('Task %s already in queue' % task_id)
        return False

    from session_manager import SessionManager
    if SessionManager.whatsapp_web_connection_okay():
        return process_new_users.apply_async(queue='process_message', task_id=task_id)
    else:
        return False


@task_postrun.connect
def postrun(sender=None, state=None, **kwargs):
    logger.info('Task postrun: %s' % sender.name)
    # if process_new_users.__name__ in sender.name:
    #     app.control.revoke('unique_process-new-users', destination=['celery@worker_q_selenium'])


@app.task(bind=True, soft_time_limit=30*60, default_retry_delay=10, max_retries=5)
def process_new_users(self):
    whatsapp_process = WhatsAppProcess()
    try:
        whatsapp_process.process_new_users()
    except Exception as e:
        self.retry(exc=e)


@app.task(bind=True, soft_time_limit=30, default_retry_delay=5, max_retries=5)
def send_message(self, delivery: Delivery):
    client.begin_transaction('send_message')
    try:
        delivery: Delivery = jsonpickle.loads(delivery, classes=[Delivery])

        if delivery.media and delivery.filename:
            logger.info('Fetching media')
            path = file_manager.download_temp_file(delivery.media, delivery.filename)
            delivery.media = path
        elif delivery.media and not delivery.filename:
            raise ValueError('"media" must have corresponding "filename"')

        if send_whatsapp(delivery):
            if delivery.media:
                file_manager.delete_temp_files()
            logger.info('Message \"%s\" sent to %s' % (delivery.__dict__, delivery.number))
        else:
            logger.error('Failed to send message', 400)
            raise ValueError('Failed to send message')

        client.end_transaction('send_message')
        return delivery
    except (ValueError, SoftTimeLimitExceeded) as e:
        client.end_transaction('send_message')
        client.capture_exception()
        self.retry(exc=e)
        alert_manager.slack_alert('***REMOVED*** ***REMOVED*** Failed to send message to number %s with txt: %s'
                                  % (delivery.number, delivery.txt))


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
    # url = None

    if deliver_voicenote and deliver_weblink:
        message = "Hello %s! Here\'s your personalized ***REMOVED***:" % schedule.name
        media = schedule.path
        url = "https://my***REMOVED***.com/***REMOVED***/%s" % schedule.***REMOVED***_token
        message = "%s %s" % (message, url)
    elif deliver_voicenote and not deliver_weblink:
        message = "Hello %s! Here\'s your personalized ***REMOVED***:" % schedule.name
        media = schedule.path
    elif not deliver_voicenote and deliver_weblink:
        message = "Hello %s! Here\'s your personalized ***REMOVED***:" % schedule.name
        url = "https://my***REMOVED***.com/***REMOVED***/%s" % schedule.***REMOVED***_token
        message = "%s %s" % (message, url)
    else:
        logger.error('***REMOVED*** failed to deliver to %s' % uid)
        alert_manager.slack_alert('***REMOVED*** ***REMOVED*** Failed to deliver ***REMOVED*** to user %s with schedule: %s'
                                  % (uid, str(schedule.__dict__)))
        return False

    params = {
        'uid': uid,
        'number': number,
        'txt': message,
        'media': media
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
