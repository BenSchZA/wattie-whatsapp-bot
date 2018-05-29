import subprocess
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

        log_manager.setup_logging()
        self.logger = log_manager.get_logger('session_manager')

    def handle_schedules(self):
        if self.handler_running:
            return

        self.handler_running = True
        self.logger.info("Handling schedules")

        self.file_manager.download_and_schedule()
        self.scheduled_deliveries_hour = self.file_manager.get_scheduled_deliveries()

        for schedule in self.scheduled_deliveries_hour:
            self.logger.info("Delivering message to %s " % schedule['uid'])
            self.logger.debug("Schedule entry: %s" % schedule)
            number = schedule['number']
            message = "\"Hello %s! Here\'s your personalized ***REMOVED***:\"" % (schedule['name'])
            media = "\"%s\"" % schedule['path']
            uid = schedule['uid']

            if self._send_***REMOVED***(number, message, media):
                self.file_manager.mark_delivered(uid)
                self.logger.info('***REMOVED*** delivered to %s' % uid)

        self.handler_running = False
        self.logger.info("Finished handling schedules")

    def is_handler_running(self):
        return self.handler_running

    @staticmethod
    def _send_***REMOVED***(number, message, media):
        try:
            subprocess.check_output(["./venv/bin/python whatsapp_cli.py --number %s --message %s --media %s"
                                     % (number, message, media)], shell=True)
            return True
        except subprocess.CalledProcessError as e:
            print(e)
            return False
