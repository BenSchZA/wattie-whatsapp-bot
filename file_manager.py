import os
import errno
import urllib.request
from urllib.parse import urlparse
import time
from datetime import datetime
from datetime import timezone
from pymongo import MongoClient
import pymongo
from pymongo.collection import Collection
from pymongo.errors import WriteError
import log_manager
from user import User
from firebase_manager import FirebaseManager
import utils

LOGS = 'logs'
DOWNLOADS = 'downloads'


class FileManager:

    def __init__(self) -> None:
        super().__init__()
        self._initialize_directories()
        self._initialize_database()
        self.logger = log_manager.get_logger('file_manager')

    def _initialize_database(self):
        self.client = MongoClient()
        self.db = self.client.file_manager
        self.firebase = FirebaseManager()

        self.downloads_collection: Collection = self.db.downloads_collection
        self.downloads_collection.create_index([("uid", pymongo.DESCENDING), ("url", pymongo.DESCENDING)], unique=True)

    def _initialize_directories(self):
        self._create_directory(LOGS)
        self._create_directory(DOWNLOADS)

    @staticmethod
    def _create_directory(directory):
        # Try create directory structure and catch any failures (i.e. already exists)
        try:
            os.makedirs(directory)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

    def download_and_schedule(self):
        firebase_scheduled = self.firebase.get_scheduled_***REMOVED***s()

        for user in firebase_scheduled:
            # Parse url and create path for download
            url = user.***REMOVED***.audio_url

            parsed = urlparse(url)
            # filename = os.path.basename(parsed.path)
            filename = user.***REMOVED***.id + '.mp3'
            pwd = os.getcwd()
            directory = pwd + '/' + DOWNLOADS + '/' + user.uid
            path = os.path.join(directory, filename)

            # Create directory structure and download file
            self._create_directory(directory)
            urllib.request.urlretrieve(url, path)

            # Create database entry for logging and management
            self._log_schedule(user, path)

    def _log_schedule(self, user: User, path):
        # Create download_collection object for insertion into database
        delivered = False
        download = {
            'id': user.***REMOVED***.id,
            'uid': user.uid,
            'name': user.username,
            'number': user.number,
            'url': user.***REMOVED***.audio_url,
            'path': path,
            'scheduled_millis': user.get_user_scheduled_time_millis_utc(),
            'delivered': delivered,
            'created_millis': utils.time_in_millis_utc(),
            'created_date': datetime.utcnow()
        }

        # Insert object into downloads_collection and log database uid
        try:
            download_id = self.downloads_collection.insert_one(download).inserted_id
            self.logger.info('File downloaded & stored in database with ID ' + str(download_id))
            return download_id
        except WriteError as e:
            self.logger.info('Entry exists for user %s & url %s' % (user.uid, user.***REMOVED***.audio_url))
            return None

    def _get_download_entry_for_uid(self, uid):
        self.downloads_collection.find_one({"uid": uid})

    def _does_uid_have_downloads(self, uid):
        return self.downloads_collection.find_one({"uid": uid}).count() > 0

    def _get_undelivered_downloads(self):
        return self.downloads_collection.find({"delivered": False,
                                               "scheduled_millis": {"$lt": utils.time_in_millis_utc()}})

    def get_scheduled_deliveries(self):
        one_hour_in_millis = 3600000
        return self.downloads_collection.find({
            "delivered": False,
            "scheduled_millis": {
                "$lt": utils.time_in_millis_utc() + one_hour_in_millis,
                "$gt": utils.time_in_millis_utc()
            }})

    def mark_delivered(self, uid):
        self.firebase.mark_***REMOVED***_delivered_now(uid)
        self.downloads_collection.update_one(
            {"uid": uid},
            {"$set": {
                "delivered": True
            }})
