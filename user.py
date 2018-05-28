from datetime import datetime
from datetime import timezone


class User:

    def __init__(self, user_dict) -> None:
        super().__init__()
        self.uid = user_dict['uid']
        self.name = user_dict['name']
        self.cell_cc = user_dict['cell_cc']
        self.cell_number = user_dict['cell_number']
        self.number = self.cell_cc + self.cell_number
        self.***REMOVED***_delivered_time_utc = user_dict['***REMOVED***_delivered_time_utc']
        self.***REMOVED***_scheduled_time_utc = user_dict['***REMOVED***_scheduled_time_utc']
        self.***REMOVED***_url = user_dict['***REMOVED***_url']

    def get_user_scheduled_time_millis_utc(self):
        now = datetime.utcnow()
        scheduled_time = datetime.strptime(self.***REMOVED***_scheduled_time_utc, '%H:%M')
        scheduled_time_utc = now.replace(hour=scheduled_time.hour, minute=scheduled_time.minute)
        scheduled_time_millis_utc = scheduled_time_utc.replace(tzinfo=timezone.utc).timestamp() * 1000
        return scheduled_time_millis_utc
