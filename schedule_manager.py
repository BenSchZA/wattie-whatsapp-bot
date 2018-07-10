import whatsapp_cli_interface
from firebase_manager import FirebaseManager
from file_manager import FileManager
import log_manager
import utils
from pymongo.collection import ObjectId
from google.api_core.exceptions import DeadlineExceeded, ServiceUnavailable


class ScheduleManager:

    def __init__(self) -> None:
        super().__init__()
        self.firebase = FirebaseManager()
        self.file_manager = FileManager()
        self.scheduled_deliveries_hour = None
        self.handler_running = False
        self.scheduler_running = False

        self.logger = log_manager.get_logger('session_manager')

    def handle_schedules(self):
        if self.handler_running:
            return
        else:
            self.handler_running = True

        self.logger.info("Handling schedules")

        self.schedule_and_deliver()

        # self.file_manager.schedule()
        # self.scheduled_deliveries_hour = self.file_manager.get_schedule()
        #
        # for schedule in self.scheduled_deliveries_hour:
        #     self.logger.info("Delivering message to %s " % schedule['uid'])
        #     self.logger.debug("Schedule entry: %s" % schedule)
        #     self.deliver_schedule(schedule)

        self.handler_running = False
        self.logger.info("Finished handling schedules")

    def schedule_and_deliver(self):
        self.logger.info("Method: schedule_and_deliver()")
        if self.scheduler_running:
            self.logger.info("Already running")
            return
        else:
            self.scheduler_running = True
            self.logger.info("Handling downloads")

        # Get list of scheduled deliveries from Firebase database
        try:
            firebase_scheduled = self.firebase.get_scheduled_***REMOVED***s()
            self.logger.info('Processing Firebase scheduled ***REMOVED***s of size %d' % len(firebase_scheduled))
        except (DeadlineExceeded, ServiceUnavailable):
            self.logger.exception("Failed handling downloads")
            return
        finally:
            self.scheduler_running = False

        # Remove and process overdue deliveries
        overdue_schedules = self.file_manager.get_overdue_schedules()
        self.logger.info('Processing overdue schedules of size %d' % overdue_schedules.count())
        for schedule in overdue_schedules:
            self.logger.error('Delivery overdue for %s' % schedule['uid'])
            self.logger.error('Removing schedule for %s' % schedule['uid'])
            self.file_manager.remove_schedule(schedule['uid'])

        # Filter scheduled deliveries
        # Remove:
        #  * delivered inside current window
        self.logger.info('Creating delivery queue')
        delivery_queue = list(filter(lambda firebase_user:
                                     not (self.file_manager.downloads_collection.find_one({
                                         "uid": firebase_user.uid,
                                         "delivered": True,
                                         "scheduled_millis": {
                                             "$lt": utils.time_in_millis_utc() + utils.ONE_HOUR_MILLIS,
                                             "$gt": utils.time_in_millis_utc()
                                         }})),
                                     firebase_scheduled))

        self.logger.info('Processing delivery queue of size %d' % len(delivery_queue))
        for user in delivery_queue:
            self.logger.info('Downloading / scheduling for %s' % user.uid)

            # Clear user db entry and downloads
            self.file_manager.remove_schedule(user.uid)

            path = ''
            if user.deliver_voicenote:
                path = self.file_manager.download_user_file(user)

            # Update/create database entry for logging and management
            self.logger.debug('Scheduled time: %s' % user.***REMOVED***.scheduled_date)

            schedule_id = self.file_manager.create_db_schedule(user, path)
            schedule = self.file_manager.downloads_collection.find_one({"_id": ObjectId(schedule_id)})

            # If schedule delivered successfully, delete user file and mark delivered, else clear schedule
            if self.deliver_schedule(schedule):
                self.file_manager.mark_delivered(schedule)
                self.file_manager.delete_user_file(user.uid)
            else:
                self.file_manager.remove_schedule(user.uid)

        self.scheduler_running = False
        self.logger.info("Finished handling downloads")

    def deliver_schedule(self, schedule):
        self.logger.info("Delivering message to %s " % schedule['uid'])
        self.logger.debug("Schedule entry: %s" % schedule)

        deliver_voicenote = schedule['deliver_voicenote']
        deliver_weblink = schedule['deliver_weblink']

        uid = schedule['uid']
        number = schedule['number']
        media = None
        url = None

        if deliver_voicenote and deliver_weblink:
            message = "Hello %s! Here\'s your personalized ***REMOVED***:" % (schedule['name'])
            media = schedule['path']
            url = "https://my***REMOVED***.com/***REMOVED***/%s" % schedule['***REMOVED***_token']
        elif deliver_voicenote and not deliver_weblink:
            message = "Hello %s! Here\'s your personalized ***REMOVED***:" % (schedule['name'])
            media = schedule['path']
        elif not deliver_voicenote and deliver_weblink:
            message = "Hello %s! Here\'s your personalized ***REMOVED***:" % (schedule['name'])
            url = "https://my***REMOVED***.com/***REMOVED***/%s" % schedule['***REMOVED***_token']
        else:
            self.logger.error('***REMOVED*** failed to deliver to %s' % uid)
            return False

        if whatsapp_cli_interface.send_whatsapp(number=number, message=message, media=media, url=url):
            self.logger.info('***REMOVED*** delivered to %s' % uid)
            return True
        else:
            self.logger.error('***REMOVED*** failed to deliver to %s' % uid)
            return False

    def is_handler_running(self):
        return self.handler_running
