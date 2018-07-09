import os
import shutil
import errno
import string
import random

from datetime import datetime
import requests

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
TEMP = 'temp'
DATA = 'data'

ONE_HOUR_MILLIS = 3600000


class FileManager:

    def __init__(self) -> None:
        super().__init__()
        self._initialize_directories()
        self._initialize_database()
        self.logger = log_manager.get_logger('file_manager')

        self.scheduler_running = False

    def _initialize_database(self):
        self.client = MongoClient('mongodb', 27017)
        self.db = self.client.file_manager
        self.firebase = FirebaseManager()

        self.downloads_collection: Collection = self.db.downloads_collection
        self.downloads_collection.create_index([("uid", pymongo.DESCENDING), ("url", pymongo.DESCENDING)], unique=True)

    def _initialize_directories(self):
        self._create_directory(LOGS)
        self._create_directory(DOWNLOADS)
        self._create_directory(DOWNLOADS + '/' + TEMP)
        self._create_directory(DATA)

    @staticmethod
    def _create_directory(directory):
        # Try create directory structure and catch any failures (i.e. already exists)
        try:
            os.makedirs(directory)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

    @staticmethod
    def create_uid(num_chars=6):
        return ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(num_chars))

    def download_temp_file(self, url, filename):
        # Configure path
        directory = self._get_temp_download_dir() + self.create_uid()
        path = os.path.join(directory, filename)

        # Create directory structure and download file
        self._create_directory(directory)
        # urllib.request.urlretrieve(url, path)
        req = requests.get(url)
        with open(path, 'wb') as file:
            self.logger.info("Saving temp file to %s" % path)
            file.write(req.content)

        return path

    def delete_temp_files(self):
        self.logger.info("Deleting temp files")
        return self._delete_path(self._get_temp_download_dir())

    def delete_user_file(self, uid):
        self._delete_path(self._get_download_dir() + uid)

    def _remove_schedule(self, uid):
        self.delete_user_file(uid)
        self.downloads_collection.delete_many({"uid": uid})

    def schedule(self):
        if self.scheduler_running:
            self.logger.info("Already running")
            return
        else:
            self.scheduler_running = True
            self.logger.info("Handling downloads")

        # Get list of scheduled deliveries from Firebase database
        try:
            firebase_scheduled = self.firebase.get_scheduled_***REMOVED***s()
        except (DeadlineExceeded, ServiceUnavailable):
            self.logger.exception("Failed handling downloads")
            return
        finally:
            self.scheduler_running = False

        # Remove and process overdue deliveries
        self.logger.info('Processing overdue schedules')
        overdue_schedules = self._get_overdue_schedules()
        for schedule in overdue_schedules:
            self.logger.error('Delivery overdue for %s' % schedule['uid'])
            self.logger.error('Removing schedule for %s' % schedule['uid'])
            self._remove_schedule(schedule['uid'])

        # Filter scheduled deliveries
        # Remove:
        #  * undelivered or
        #  * delivered inside current window
        self.logger.info('Creating download queue')
        download_queue = list(filter(lambda firebase_user:
                                     not (self.downloads_collection.find_one({
                                        "uid": firebase_user.uid,
                                        "delivered": False
                                        }) or self.downloads_collection.find_one({
                                         "uid": firebase_user.uid,
                                         "delivered": True,
                                         "scheduled_millis": {
                                             "$lt": utils.time_in_millis_utc() + ONE_HOUR_MILLIS,
                                             "$gt": utils.time_in_millis_utc()
                                         }})),
                                     firebase_scheduled))

        self.logger.info('Processing download queue')
        for user in download_queue:
            self.logger.info('Downloading / scheduling for %s' % user.uid)

            # Clear user db entry and downloads
            self._remove_schedule(user.uid)

            path = ''
            if user.deliver_voicenote:
                # Configure path
                filename = user.***REMOVED***.id + '.mp3'
                directory = self._get_download_dir() + user.uid
                path = os.path.join(directory, filename)

                # Create directory structure and download file
                self._create_directory(directory)
                # urllib.request.urlretrieve(user.***REMOVED***.audio_url, path)
                req = requests.get(user.***REMOVED***.audio_url)
                with open(path, 'wb') as file:
                    file.write(req.content)
                self.logger.debug('Downloaded file for user %s' % user.***REMOVED***.scheduled_date)

            # Update/create database entry for logging and management
            self._create_db_schedule(user, path)
            self.logger.debug('Scheduled time: %s' % user.***REMOVED***.scheduled_date)

        self.scheduler_running = False
        self.logger.info("Finished handling downloads")

    def _create_db_schedule(self, user: User, path):
        # Create download_collection object for insertion into database
        delivered = False
        download = {
            'id': user.***REMOVED***.id,
            'uid': user.uid,
            'name': user.username,
            'number': user.number,
            'url': user.***REMOVED***.audio_url,
            '***REMOVED***_token': user.***REMOVED***_token,
            'path': path,
            'scheduled_millis': user.***REMOVED***.scheduled_date.timestamp() * 1000,
            'deliver_voicenote': user.deliver_voicenote,
            'deliver_weblink': user.deliver_weblink,
            'delivered': delivered,
            'created_millis': utils.time_in_millis_utc(),
            'created_date': datetime.utcnow()
        }

        # Insert object into downloads_collection and log database uid
        try:
            download_id = self.downloads_collection.insert_one(download).inserted_id
            self.logger.info('Schedule in database with ID ' + str(download_id))
            return download_id
        except WriteError as e:
            self.logger.info('Entry exists for user %s & url %s' % (user.uid, user.***REMOVED***.audio_url))
            return None

    def get_schedule(self):
        schedule = self.downloads_collection.find({
            "delivered": False,
            "scheduled_millis": {
                "$lt": utils.time_in_millis_utc() + ONE_HOUR_MILLIS,
                "$gt": utils.time_in_millis_utc()
            }})
        return schedule

    def mark_delivered(self, uid, ***REMOVED***_id):
        self.firebase.mark_***REMOVED***_delivered_now(uid, ***REMOVED***_id)
        self.downloads_collection.update_one(
            {"uid": uid},
            {"$set": {
                "delivered": True
            }})

    @staticmethod
    def _get_download_dir():
        pwd = os.getcwd()
        return pwd + '/' + DOWNLOADS + '/'

    @staticmethod
    def _get_temp_download_dir():
        pwd = os.getcwd()
        return pwd + '/' + DOWNLOADS + '/' + TEMP + '/'

    def _delete_path(self, path):
        self.logger.info("Removing path %s" % path)
        try:
            shutil.rmtree(path)
            self.logger.info("Path removed")
            return True
        except FileNotFoundError:
            self.logger.info("Path not found")
            return False

    def _get_download_entry_for_uid(self, uid):
        self.downloads_collection.find_one({"uid": uid})

    def _does_uid_have_downloads(self, uid):
        return self.downloads_collection.find_one({"uid": uid}).count() > 0

    def _get_overdue_schedules(self):
        return self.downloads_collection.find({"delivered": False,
                                               "scheduled_millis": {"$lt": utils.time_in_millis_utc()}
                                               })
