import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

import time
from user import User

# https://firebase.google.com/docs/firestore/query-data/get-data
# https://firebase.google.com/docs/firestore/query-data/queries
# https://firebase.google.com/docs/firestore/query-data/order-limit-data

MILLIS_24_HOURS = 86400000
MILLIS_01_HOURS = 3600000
FIREBASE_APP_NAME = '***REMOVED***'


class FirebaseManager:

    def __init__(self) -> None:
        super().__init__()
        # Use a service account
        try:
            initialized = firebase_admin._DEFAULT_APP_NAME in firebase_admin._apps
        except ValueError:
            initialized = False

        if not initialized:
            cred = credentials.Certificate('***REMOVED***/'
                                           '***REMOVED***')
            firebase_admin.initialize_app(cred)

        self.db = firestore.client()

    @staticmethod
    def _current_millis():
        return time.time() * 1000

    def _get_users_ref(self):
        return self.db.collection(u'users')

    def _get_users(self):
        return self._get_users_ref().get()

    def _get_user(self, uid):
        return self._get_users_ref().document(uid)

    def _get_user_ids(self):
        ids = []
        users = self._get_users()
        for doc in users:
            ids.append(doc.id)
        return ids

    def _get_scheduled_deliveries_day(self):
        scheduled = []
        users = self._get_users()
        for doc in users:
            user = User(doc.to_dict())

            if user.***REMOVED***_delivered_time_utc < (self._current_millis() - MILLIS_24_HOURS):
                scheduled.append(user)
        return scheduled

    def get_scheduled_deliveries_hour(self):
        scheduled = []
        scheduled_day = self._get_scheduled_deliveries_day()

        for user in scheduled_day:
            current_time_millis_utc = self._current_millis()
            scheduled_time_millis_utc = user.get_user_scheduled_time_millis_utc()
            interval_time_millis_utc = self._current_millis() + MILLIS_01_HOURS

            if current_time_millis_utc < scheduled_time_millis_utc < interval_time_millis_utc:
                scheduled.append(user)
        return scheduled

    def mark_***REMOVED***_delivered_now(self, uid):
        doc: firestore.firestore.DocumentReference = self._get_user(uid)
        doc.update({
            u'***REMOVED***_delivered_time_utc': self._current_millis()
        })
