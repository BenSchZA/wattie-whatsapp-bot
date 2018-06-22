import os
import shutil
import errno

from datetime import datetime
import urllib.request

import pymongo
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.errors import WriteError

from google.api_core.exceptions import DeadlineExceeded, ServiceUnavailable

import log_manager
from firebase_manager import FirebaseManager
from user import User

import utils


LOGS = 'logs'
DOWNLOADS = 'downloads'
DATA = 'data'


class FileManager:

    def __init__(self) -> None:
        super().__init__()
        self._initialize_directories()
        self._initialize_database()
        self.logger = log_manager.get_logger('file_manager')

        self.downloader_running = False

    def _initialize_database(self):
        self.client = MongoClient('mongodb', 27017)
        self.db = self.client.file_manager
        self.firebase = FirebaseManager()

        self.downloads_collection: Collection = self.db.downloads_collection
        self.downloads_collection.create_index([("uid", pymongo.DESCENDING), ("url", pymongo.DESCENDING)], unique=True)

    def _initialize_directories(self):
        self._create_directory(LOGS)
        self._create_directory(DOWNLOADS)
        self._create_directory(DATA)

    @staticmethod
    def _create_directory(directory):
        # Try create directory structure and catch any failures (i.e. already exists)
        try:
            os.makedirs(directory)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

    def download_and_schedule(self):
        if self.downloader_running:
            return
        else:
            self.downloader_running = True

        self.logger.info("Handling downloads")

        try:
            firebase_scheduled = self.firebase.get_scheduled_***REMOVED***s()
        except (DeadlineExceeded, ServiceUnavailable):
            self.logger.exception("Failed handling downloads")
            return
        finally:
            self.downloader_running = False

        for user in firebase_scheduled:
            # Clear user downloads
            # TODO: check that files aren't being redownloaded
            self._remove_user_downloads(user.uid)
            self.downloads_collection.delete_many({"uid": user.uid})

            # Configure path
            filename = user.***REMOVED***.id + '.mp3'
            directory = self._get_download_dir() + user.uid
            path = os.path.join(directory, filename)

            # Create directory structure and download file
            self._create_directory(directory)
            urllib.request.urlretrieve(user.***REMOVED***.audio_url, path)

            # Create database entry for logging and management
            self._schedule(user, path)

        self.downloader_running = False
        self.logger.info("Finished handling downloads")

    def _schedule(self, user: User, path):
        # Create download_collection object for insertion into database
        delivered = False
        download = {
            'id': user.***REMOVED***.id,
            'uid': user.uid,
            'name': user.username,
            'number': user.number,
            'url': user.***REMOVED***.audio_url,
            'path': path,
            'scheduled_millis': user.***REMOVED***.scheduled_date.utcnow().timestamp() * 1000,
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

    def get_schedule(self):
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

    @staticmethod
    def _get_download_dir():
        pwd = os.getcwd()
        return pwd + '/' + DOWNLOADS + '/'

    def _remove_user_downloads(self, uid):
        self.logger.info("Removing user %s downloads" % uid)
        try:
            shutil.rmtree(self._get_download_dir() + uid)
        except FileNotFoundError:
            pass

    def _get_download_entry_for_uid(self, uid):
        self.downloads_collection.find_one({"uid": uid})

    def _does_uid_have_downloads(self, uid):
        return self.downloads_collection.find_one({"uid": uid}).count() > 0

    def _get_undelivered_downloads(self):
        return self.downloads_collection.find({"delivered": False,
                                               "scheduled_millis": {"$lt": utils.time_in_millis_utc()}})
