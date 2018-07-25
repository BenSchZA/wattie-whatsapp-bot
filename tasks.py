from pymongo.collection import ObjectId
import os
import requests
import jsonpickle

import log_manager
from file_manager import FileManager
from user import User
from schedule import Schedule

from kombu import Queue
from celery import Celery
from celery.exceptions import SoftTimeLimitExceeded
from celery.exceptions import MaxRetriesExceededError

app = Celery('tasks', broker='redis://redis')

app.conf.task_queues = (
    Queue('download'),
    Queue('deliver')
)

file_manager = FileManager()
logger = log_manager.get_logger('session_manager')


def purge_tasks():
    app.control.purge()


def queue_download_and_deliver(user: User):
    user_json = jsonpickle.dumps(user)

    download_and_deliver.apply_async(args=[user_json], queue='download')


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

        # TODO:
        user.number = '27763381243'
        schedule.number = '27763381243'

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
            file_manager.mark_delivered(schedule)
            file_manager.delete_user_file(user.uid)
            user.***REMOVED***.delivered = True
            return True
        else:
            user.***REMOVED***.delivered = False
            self.retry(exc=Exception('Delivery failed'))
            # self.alert_manager.slack_alert('***REMOVED*** ***REMOVED*** Failed to deliver ***REMOVED*** to user %s with schedule: \n\n%s'
            #                                % (user.uid, str(schedule)))

    except Exception as exc:
        if isinstance(exc, SoftTimeLimitExceeded):
            try:
                self.retry(exc=exc)
            except MaxRetriesExceededError:
                logger.error('Max retries exceeded')
                file_manager.delete_user_file(user.uid)
                file_manager.remove_schedule(user.uid)
                download_and_deliver.apply_async(args=[user_json], queue='download')
        else:
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

    message = '''Today's Burning Question: Are the security guards at Samsung called the Guardians of the Galaxy? As you make your way to the end of Hump Day, you can start getting excited for your ***REMOVED*** tomorrow. What to expect? That time meat fell from the sky, Wackhead Simpson's Senseless Survey, Barack Obama's speech last week, bizarre quiz questions and a company that trialed a 4 day work week. Have a lovely evening my dudu bear.'''

    # uid = schedule.uid
    # number = schedule.number
    # media = None
    # url = None
    #
    # if deliver_voicenote and deliver_weblink:
    #     message = "Hello %s! Here\'s your personalized ***REMOVED***:" % schedule.name
    #     media = schedule.path
    #     url = "https://my***REMOVED***.com/***REMOVED***/%s" % schedule.***REMOVED***_token
    # elif deliver_voicenote and not deliver_weblink:
    #     message = "Hello %s! Here\'s your personalized ***REMOVED***:" % schedule.name
    #     media = schedule.path
    # elif not deliver_voicenote and deliver_weblink:
    #     message = "Hello %s! Here\'s your personalized ***REMOVED***:" % schedule.name
    #     url = "https://my***REMOVED***.com/***REMOVED***/%s" % schedule.***REMOVED***_token
    # else:
    #     logger.error('***REMOVED*** failed to deliver to %s' % uid)
    #     return False

    params = {
        'uid': uid,
        'number': number,
        'message': message,
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
        return False
