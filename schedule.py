from user import User
import utils
from datetime import datetime


class Schedule:

    def __init__(self, user: User, path):
        self.id = user.***REMOVED***.id
        self.uid = user.uid
        self.name = user.username
        self.number = user.number
        self.url = user.***REMOVED***.audio_url
        self.***REMOVED***_token = user.***REMOVED***_token
        self.path = path
        self.scheduled_millis = user.***REMOVED***.scheduled_date.timestamp() * 1000
        self.deliver_voicenote = user.deliver_voicenote
        self.deliver_weblink = user.deliver_weblink
        self.delivered = False
        self.created_millis = utils.time_in_millis_utc()
        self.created_date = datetime.utcnow()
