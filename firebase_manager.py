import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from google.cloud.exceptions import NotFound

import os
import time
from datetime import datetime
from datetime import timedelta
from domain.user import User
from logging_config import log_manager
import utils

# https://firebase.google.com/docs/firestore/query-data/get-data
# https://firebase.google.com/docs/firestore/query-data/queries
# https://firebase.google.com/docs/firestore/query-data/order-limit-data

FIREBASE_APP_NAME = 'REMOVED'


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

    def _get_active_subs_in_window(self):
        now = datetime.utcnow()
        window_start = now - timedelta(hours=int(os.environ['DELIVERY_WINDOW_HOURS_BEFORE_AND_AFTER']))
        window_end = now + timedelta(hours=int(os.environ['DELIVERY_WINDOW_HOURS_BEFORE_AND_AFTER']))

        return self._get_users_ref().where(u'activeSubscription', u'==', True) \
            .where(u'nextREMOVEDDate', u'>=', window_start) \
            .where(u'nextREMOVEDDate', u'<=', window_end) \
            .get()

    def _get_REMOVED(self, uid, REMOVED_id):
        try:
            return next(self._get_user(uid).collection(u'REMOVEDs')
                        .where(u'REMOVEDUID', u'==', REMOVED_id)
                        .limit(1).get())
        except (NotFound, StopIteration):
            self.logger.debug('Failed to get REMOVED with id %s for user %s' % (REMOVED_id, uid))
            return None

    def get_scheduled_REMOVEDs(self):
        scheduled = []
        now = datetime.utcnow()
        window_start = now - timedelta(hours=int(os.environ['DELIVERY_WINDOW_HOURS_BEFORE_AND_AFTER']))
        window_end = now + timedelta(hours=int(os.environ['DELIVERY_WINDOW_HOURS_BEFORE_AND_AFTER']))

        # Generators within generators are dark magic and do not work!
        len_subs_in_window = utils.generator_len(self._get_active_subs_in_window())
        subs_in_window = list(self._get_active_subs_in_window())

        self.logger.debug('%d active subs scheduled for next hour' % len_subs_in_window)

        no_valid_REMOVEDs = 0
        for doc in subs_in_window:
            try:
                user_uid = doc.id
                user_dict = doc.to_dict()

                REMOVEDs = self._get_user(user_uid).collection(u'REMOVEDs')
                scheduled_REMOVED_gen = REMOVEDs \
                    .where(u'delivered', u'==', False) \
                    .where(u'scheduledDate', u'>=', window_start)\
                    .where(u'scheduledDate', u'<=', window_end) \
                    .limit(1).get()

                scheduled_REMOVED = next(scheduled_REMOVED_gen)

                if scheduled_REMOVED:
                    REMOVED_id = scheduled_REMOVED.id
                    REMOVED_dict = scheduled_REMOVED.to_dict()
                    user = User(user_dict, REMOVED_dict, REMOVED_id)
                    scheduled.append(user)

            except (NotFound, StopIteration):
                no_valid_REMOVEDs += 1
                continue

        self.logger.debug('%d of %d active subs have no valid REMOVEDs' % (no_valid_REMOVEDs, len_subs_in_window))
        return scheduled

    def _get_user_ids(self):
        ids = []
        users = self._get_users()
        for doc in users:
            ids.append(doc.id)
        return ids

    def mark_REMOVED_delivered_now(self, uid, REMOVED_id):
        doc: firestore.firestore.DocumentSnapshot = self._get_REMOVED(uid, REMOVED_id)
        doc_ref: firestore.firestore.DocumentReference = doc.reference

        if doc_ref:
            doc_ref.update({
                u'delivered': True
            })
            self.logger.debug('Marked REMOVED delivered for user %s and doc id %s' % (uid, doc_ref.id))
        else:
            self.logger.debug('Failed to mark REMOVED delivered for user %s and doc id %s' % (uid, doc_ref.id))
