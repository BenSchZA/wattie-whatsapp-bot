import whatsapp_cli_interface
from firebase_manager import FirebaseManager
from file_manager import FileManager
import log_manager
import utils
from pymongo.collection import ObjectId
from google.api_core.exceptions import DeadlineExceeded, ServiceUnavailable
from alert_manager import AlertManager
import requests
import os
import elasticapm
import tasks


class ScheduleManager:

    def __init__(self) -> None:
        super().__init__()
        self.firebase = FirebaseManager()
        self.file_manager = FileManager()
        self.alert_manager = AlertManager()
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
            self.file_manager.delete_user_file(schedule['uid'])
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
                                             "$lt": utils.time_in_millis_utc() + utils.MILLIS_1_HOUR,
                                             "$gt": utils.time_in_millis_utc()
                                         }
                                     })),
                                     firebase_scheduled))

        delivery_queue = firebase_scheduled

        self.logger.info('Processing delivery queue of size %d' % len(delivery_queue))
        self._process_delivery_queue(delivery_queue)

        # number_delivered = len(list(filter(lambda queue_entry: queue_entry.racast.delivered, delivery_queue)))

        # if len(delivery_queue) > 0:
        #     self.alert_manager.slack_alert('Delivered %d of %d ***REMOVED***s in queue.'
        #                                    % (number_delivered, len(delivery_queue)))

        self.scheduler_running = False
        self.logger.info("Finished handling downloads")

    @elasticapm.capture_span()
    def _process_delivery_queue(self, delivery_queue):
        for user in delivery_queue:
            self.logger.info('Downloading / scheduling for %s' % user.uid)

            # Download and deliver
            tasks.queue_download_and_deliver(user)

    def is_handler_running(self):
        return self.handler_running
