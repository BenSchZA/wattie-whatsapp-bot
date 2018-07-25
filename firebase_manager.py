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
import utils

# https://firebase.google.com/docs/firestore/query-data/get-data
# https://firebase.google.com/docs/firestore/query-data/queries
# https://firebase.google.com/docs/firestore/query-data/order-limit-data

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
            # cred = credentials.Certificate('***REMOVED***/***REMOVED***')
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

    def _get_***REMOVED***(self, uid, ***REMOVED***_id):
        try:
            return next(self._get_user(uid).collection(u'***REMOVED***s')
                        .where(u'***REMOVED***UID', u'==', ***REMOVED***_id)
                        .limit(1).get())
        except (NotFound, StopIteration):
            self.logger.debug('Failed to get ***REMOVED*** with id %s for user %s' % (***REMOVED***_id, uid))
            return None

    def get_scheduled_***REMOVED***s(self):
        scheduled = []
        now = datetime.utcnow()
        now_plus_one_hour = now + timedelta(hours=1)

        # Generators within generators are dark magic and do not work!
        len_subs_next_hour = utils.generator_len(self._get_active_subs_next_hour())
        subs_next_hour = list(self._get_active_subs_next_hour())

        self.logger.debug('%d active subs scheduled for next hour' % len_subs_next_hour)

        no_valid_***REMOVED***s = 0
        for doc in subs_next_hour:
            try:
                user_uid = doc.id
                user_dict = doc.to_dict()

                ***REMOVED***s = self._get_user(user_uid).collection(u'***REMOVED***s')
                scheduled_***REMOVED***_gen = ***REMOVED***s \
                    .where(u'delivered', u'==', False) \
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
                no_valid_***REMOVED***s += 1
                continue

        self.logger.debug('%d of %d active subs have no valid ***REMOVED***s' % (no_valid_***REMOVED***s, len_subs_next_hour))
        return scheduled

    def _get_user_ids(self):
        ids = []
        users = self._get_users()
        for doc in users:
            ids.append(doc.id)
        return ids

    def mark_***REMOVED***_delivered_now(self, uid, ***REMOVED***_id):
        doc: firestore.firestore.DocumentSnapshot = self._get_***REMOVED***(uid, ***REMOVED***_id)
        doc_ref: firestore.firestore.DocumentReference = doc.reference

        if doc_ref:
            doc_ref.update({
                u'delivered': True
            })
            self.logger.debug('Marked ***REMOVED*** delivered for user %s and doc id %s' % (uid, doc_ref.id))
        else:
            self.logger.debug('Failed to mark ***REMOVED*** delivered for user %s and doc id %s' % (uid, doc_ref.id))
