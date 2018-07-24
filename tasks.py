import tasktiger
from redis import Redis

import elasticapm
from pymongo.collection import ObjectId
import os
import requests
import jsonpickle

import log_manager
from file_manager import FileManager
from user import User
from schedule import Schedule

from celery import Celery
app = Celery('tasks', broker='redis://redis')


@app.task
def add(x, y):
    return x + y


file_manager = FileManager()
logger = log_manager.get_logger('session_manager')

conn = Redis(host='redis', db=1, decode_responses=True)

tiger = tasktiger.TaskTiger(connection=conn, config={
    'BATCH_QUEUES': {
        'download': os.environ['NUM_WORKERS'],
        'deliver': 1
    }
})


def queue_download_and_deliver(user: User):
    # user_json = json.dumps(user, cls=utils.DefaultJSONEncoder)
    user_json = jsonpickle.dumps(user)

    tiger.delay(func=_download_and_deliver, args=(user_json,), retry=True, retry_method=tasktiger.linear(5, 5, 3))


def _queue_delivery(user: User, schedule: Schedule):
    # user_json = json.dumps(user, cls=utils.DefaultJSONEncoder)
    # schedule_json = json.dumps(schedule, cls=utils.DefaultJSONEncoder)
    user_json = jsonpickle.dumps(user)
    schedule_json = jsonpickle.dumps(schedule)

    tiger.delay(func=_deliver, args=(user_json, schedule_json,), retry=False, unique=True)
    # when=datetime.utcnow()


@elasticapm.capture_span()
@tiger.task(queue='download', hard_timeout=25)
def _download_and_deliver(user):
    user: User = jsonpickle.loads(user, classes=[User, User.***REMOVED***, Schedule])

    # Clear user db entry and downloads
    if file_manager.does_path_exist(file_manager.get_user_download_path(user.uid)):
        file_manager.remove_schedule(user.uid)

    path = ''
    if user.deliver_voicenote:
        with elasticapm.capture_span('download_user_file'):
            path = file_manager.download_user_file(user)

    # Update/create database entry for logging and management
    logger.debug('Scheduled time: %s' % user.***REMOVED***.scheduled_date)

    schedule_id = file_manager.create_db_schedule(user, path)

    schedule = file_manager.downloads_collection.find_one({"_id": ObjectId(schedule_id)})
    schedule = Schedule(user, schedule['path'])

    user.number = '27763381243'
    schedule.number = '27763381243'
    _queue_delivery(user, schedule)


@elasticapm.capture_span()
@tiger.task(queue='deliver', hard_timeout=30)
def _deliver(user, schedule):
    user: User = jsonpickle.loads(user, classes=[User, User.***REMOVED***, Schedule])
    schedule = jsonpickle.loads(schedule, classes=[User, User.***REMOVED***, Schedule])

    if user.deliver_voicenote and not file_manager.does_path_exist(file_manager.get_user_download_path(user.uid)):
        user_json = jsonpickle.dumps(user)
        schedule_json = jsonpickle.dumps(schedule)
        task = tasktiger.Task(tiger, _deliver, args=[user_json, schedule_json], unique=True)
        task.cancel()
        queue_download_and_deliver(user)
        raise Exception('User download not available')

    # If schedule delivered successfully, delete user file and mark delivered, else clear schedule
    if _deliver_schedule(schedule):
        # file_manager.mark_delivered(schedule)
        file_manager.delete_user_file(user.uid)
        user.***REMOVED***.delivered = True
    else:
        file_manager.remove_schedule(user.uid)
        user.***REMOVED***.delivered = False
        # self.alert_manager.slack_alert('***REMOVED*** ***REMOVED*** Failed to deliver ***REMOVED*** to user %s with schedule: \n\n%s'
        #                                % (user.uid, str(schedule)))


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
        return False

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
