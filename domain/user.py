from datetime import datetime
from datetime import timezone


class User:

    def __init__(self, user_dict, ***REMOVED***_dict, ***REMOVED***_id='') -> None:
        super().__init__()
        self.uid = user_dict['uid']
        self.username = user_dict['username']
        self.***REMOVED***_token = user_dict['***REMOVED***Token']
        self._mobile_num_prefix = user_dict['mobileNumPrefix'] if user_dict['mobileNumPrefix'] else ''
        self._mobile_num = user_dict['mobileNum'] if user_dict['mobileNum'] else ''
        self.number = self._mobile_num_prefix + self._mobile_num
        self.active_subscription = user_dict['activeSubscription']
        self.next_***REMOVED***_date = user_dict['next***REMOVED***Date']
        self.***REMOVED*** = self.***REMOVED***(***REMOVED***_id=***REMOVED***_id, ***REMOVED***_dict=***REMOVED***_dict) if ***REMOVED***_dict else None
        self.deliver_weblink = user_dict['deliverWebLink']
        self.deliver_voicenote = user_dict['deliverVoicenote']

    class ***REMOVED***:

        def __init__(self, ***REMOVED***_dict, ***REMOVED***_id='') -> None:
            super().__init__()
            self.id = ***REMOVED***_id
            self.delivered = ***REMOVED***_dict['delivered']
            self.scheduled_date: datetime = ***REMOVED***_dict['scheduledDate']
            self.audio_url = ***REMOVED***_dict['audioURL']

    def get_user_scheduled_time_millis_utc(self):
        now = datetime.utcnow()
        scheduled_time = datetime.strptime(self.***REMOVED***.scheduled_time_utc, '%H:%M')
        scheduled_time_utc = now.replace(hour=scheduled_time.hour, minute=scheduled_time.minute)
        scheduled_time_millis_utc = scheduled_time_utc.replace(tzinfo=timezone.utc).timestamp() * 1000
        return scheduled_time_millis_utc
