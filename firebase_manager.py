import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from google.cloud.exceptions import NotFound

import os
import time
from datetime import datetime
from datetime import timedelta
import pytz
from user import User
import log_manager

# https://firebase.google.com/docs/firestore/query-data/get-data
# https://firebase.google.com/docs/firestore/query-data/queries
# https://firebase.google.com/docs/firestore/query-data/order-limit-data

MILLIS_24_HOURS = 86400000
MILLIS_01_HOURS = 3600000
FIREBASE_APP_NAME = '***REMOVED***'


class FirebaseManager:

    def __init__(self) -> None:
        super().__init__()
        self.logger = log_manager.get_logger('firebase_manager')

        self.logger.info('Starting Firebase manager')

        # Use a service account
        try:
            initialized = firebase_admin._DEFAULT_APP_NAME in firebase_admin._apps
        except ValueError:
            initialized = False

        if not initialized:
            self.logger.info('Firebase not initialized')
            cred = credentials.Certificate(os.environ['FIREBASE_CERTIFICATE_LOCATION'])
            firebase_admin.initialize_app(cred)
        else:
            self.logger.info('Firebase initialized')

        self.db = firestore.client()
        self.logger.info('Firebase manager started')

    @staticmethod
    def _current_millis():
        return time.time() * 1000

    def _get_users_ref(self):
        return self.db.collection(u'users')

    def _get_users(self):
        return self._get_users_ref().get()

    def _get_user(self, uid):
        return self._get_users_ref().document(uid)

    def _get_active_subs_next_hour(self):
        now = datetime.utcnow()
        now_plus_one_hour = now + timedelta(hours=1)

        return self._get_users_ref().where(u'activeSubscription', u'==', True) \
            .where(u'next***REMOVED***Date', u'>=', now) \
            .where(u'next***REMOVED***Date', u'<=', now_plus_one_hour) \
            .get()

    def _get_todays_***REMOVED***(self, uid):
        today = datetime.utcnow().date()
        today_start = datetime(today.year, today.month, today.day, tzinfo=pytz.UTC)
        today_end = today_start + timedelta(1)

        try:
            return next(self._get_user(uid).collection(u'***REMOVED***s')
                        .where(u'scheduledDate', u'>=', today_start)
                        .where(u'scheduledDate', u'<=', today_end)
                        .limit(1).get())
        except (NotFound, StopIteration):
            self.logger.debug('Failed to get today\'s ***REMOVED*** for user %s' % uid)
            return None

    def get_scheduled_***REMOVED***s(self):
        scheduled = []
        now = datetime.utcnow()
        now_plus_one_hour = now + timedelta(hours=1)

        subs_next_hour = self._get_active_subs_next_hour()
        for doc in subs_next_hour:
            try:
                user_uid = doc.id
                user_dict = doc.to_dict()

                ***REMOVED***s = self._get_user(user_uid).collection(u'***REMOVED***s')
                scheduled_***REMOVED***_gen = ***REMOVED***s\
                    .where(u'delivered', u'==', False)\
                    .where(u'scheduledDate', u'>=', now)\
                    .where(u'scheduledDate', u'<=', now_plus_one_hour) \
                    .limit(1).get()
                scheduled_***REMOVED*** = next(scheduled_***REMOVED***_gen)

                if scheduled_***REMOVED***:
                    ***REMOVED***_id = scheduled_***REMOVED***.id
                    ***REMOVED***_dict = scheduled_***REMOVED***.to_dict()
                    user = User(user_dict, ***REMOVED***_dict, ***REMOVED***_id)
                    scheduled.append(user)

            except (NotFound, StopIteration):
                continue

        return scheduled

    def _get_user_ids(self):
        ids = []
        users = self._get_users()
        for doc in users:
            ids.append(doc.id)
        return ids

    def mark_***REMOVED***_delivered_now(self, uid):
        doc: firestore.firestore.DocumentSnapshot = self._get_todays_***REMOVED***(uid)
        doc_ref: firestore.firestore.DocumentReference = doc.reference
        if doc_ref:
            doc_ref.update({
                u'delivered': True
            })
            self.logger.info('Marked ***REMOVED*** delivered for user %s' % uid)
        else:
            self.logger.info('Failed to mark ***REMOVED*** delivered for user %s' % uid)
