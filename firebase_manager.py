import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from google.cloud.exceptions import NotFound

import time
from datetime import datetime
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

    def _get_users_active_subscription(self):
        return self._get_users_ref().where(u'activeSubscription', u'==', True).get()

    def _get_todays_***REMOVED***(self, uid):
        try:
            today = datetime.utcnow().strftime('%Y-%m-%d')
            return next(self._get_user(uid).collection(u'***REMOVED***s')
                        .where(u'scheduledDate', u'==', today).limit(1).get())
        except NotFound:
            return None

    def get_scheduled_***REMOVED***s(self):
        scheduled = []
        today = datetime.utcnow().strftime('%Y-%m-%d')

        for doc in self._get_users_active_subscription():
            try:
                user_uid = doc.id
                user_dict = doc.to_dict()
                todays_***REMOVED***_doc_gen = self._get_user(user_uid).collection(u'***REMOVED***s') \
                    .where(u'scheduledDate', u'==', today).limit(1).get()
                todays_***REMOVED***_doc = next(todays_***REMOVED***_doc_gen)

                ***REMOVED***_id = todays_***REMOVED***_doc.id
                ***REMOVED***_dict = todays_***REMOVED***_doc.to_dict()

                user = User(user_dict, ***REMOVED***_dict, ***REMOVED***_id)

                current_time_millis_utc = self._current_millis()
                scheduled_time_millis_utc = user.get_user_scheduled_time_millis_utc()
                interval_time_millis_utc = self._current_millis() + MILLIS_01_HOURS

                if (current_time_millis_utc < scheduled_time_millis_utc < interval_time_millis_utc)\
                        and not user.***REMOVED***.delivered:
                    scheduled.append(user)

            except (NotFound, StopIteration, GeneratorExit):
                pass

        return scheduled

    def _get_user_ids(self):
        ids = []
        users = self._get_users()
        for doc in users:
            ids.append(doc.id)
        return ids

    # def _get_scheduled_deliveries_day(self):
    #     scheduled = []
    #     users = self._get_users()
    #
    #     for doc in users:
    #         user_dict = doc.to_dict()
    #         ***REMOVED***_dict = self._get_todays_***REMOVED***(user_dict['uid'])
    #
    #         user = User(user_dict, ***REMOVED***_dict)
    #
    #         if user.***REMOVED***.delivered_time_utc < (self._current_millis() - MILLIS_24_HOURS):
    #             scheduled.append(user)
    #     return scheduled

    # def get_scheduled_deliveries_hour(self):
    #     scheduled = []
    #     scheduled_day = self._get_scheduled_deliveries_day()
    #
    #     for user in scheduled_day:
    #         current_time_millis_utc = self._current_millis()
    #         scheduled_time_millis_utc = user.get_user_scheduled_time_millis_utc()
    #         interval_time_millis_utc = self._current_millis() + MILLIS_01_HOURS
    #
    #         if current_time_millis_utc < scheduled_time_millis_utc < interval_time_millis_utc:
    #             scheduled.append(user)
    #     return scheduled

    def mark_***REMOVED***_delivered_now(self, uid):
        doc: firestore.firestore.DocumentSnapshot = self._get_todays_***REMOVED***(uid)
        doc_ref: firestore.firestore.DocumentReference = doc.reference
        if doc_ref:
            doc_ref.update({
                u'delivered': True
            })
