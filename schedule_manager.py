import whatsapp_cli_interface
from firebase_manager import FirebaseManager
from file_manager import FileManager
import log_manager


class ScheduleManager:

    def __init__(self) -> None:
        super().__init__()
        self.firebase = FirebaseManager()
        self.file_manager = FileManager()
        self.scheduled_deliveries_hour = None
        self.handler_running = False

        self.logger = log_manager.get_logger('session_manager')

    def handle_schedules(self):
        if self.handler_running:
            return
        else:
            self.handler_running = True

        self.logger.info("Handling schedules")

        self.file_manager.schedule()
        self.scheduled_deliveries_hour = self.file_manager.get_schedule()

        for schedule in self.scheduled_deliveries_hour:
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
                self.logger.info('***REMOVED*** not delivered to %s' % uid)
                return

            if whatsapp_cli_interface.send_whatsapp(number=number, message=message, media=media, url=url):
                self.file_manager.mark_delivered(uid, schedule['id'])
                self.file_manager.delete_user_file(uid)
                self.logger.info('***REMOVED*** delivered to %s' % uid)
            else:
                self.logger.error('***REMOVED*** failed to deliver to %s' % uid)

        self.handler_running = False
        self.logger.info("Finished handling schedules")

    def is_handler_running(self):
        return self.handler_running
