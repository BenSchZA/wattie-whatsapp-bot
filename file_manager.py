import os
import shutil
import errno
import string
import random

import requests

import pymongo
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.errors import WriteError

from google.api_core.exceptions import DeadlineExceeded, ServiceUnavailable

from logging_config import log_manager
from firebase_manager import FirebaseManager
from domain.user import User
from domain.schedule import Schedule

import utils


LOGS = 'logs'
DOWNLOADS = 'downloads'
TEMP = 'temp'
DATA = 'data'


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

    def delete_download_files(self):
        self.logger.info("Deleting download files")
        return self._delete_path(self._get_download_dir())

    def schedule(self):
        self.logger.info("Method: schedule()")
        if self.scheduler_running:
            self.logger.info("Already running")
            return
        else:
            self.scheduler_running = True
            self.logger.info("Handling downloads")

        # Get list of scheduled deliveries from Firebase database
        try:
            firebase_scheduled = self.firebase.get_scheduled_REMOVEDs()
        except (DeadlineExceeded, ServiceUnavailable):
            self.logger.exception("Failed handling downloads")
            return
        finally:
            self.scheduler_running = False

        # Remove and process overdue deliveries
        self.logger.info('Processing overdue schedules')
        overdue_schedules = self.get_overdue_schedules()
        for schedule in overdue_schedules:
            self.logger.error('Delivery overdue for %s' % schedule['uid'])
            self.logger.error('Removing schedule for %s' % schedule['uid'])
            self.delete_user_file(schedule['uid'])
            self.remove_schedule(schedule['uid'])

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
                                             "$lt": utils.time_in_millis_utc() + utils.MILLIS_1_HOUR,
                                             "$gt": utils.time_in_millis_utc()
                                         }})),
                                     firebase_scheduled))

        self.logger.info('Processing download queue')
        for user in download_queue:
            self.logger.info('Downloading / scheduling for %s' % user.uid)

            # Clear user db entry and downloads
            self.delete_user_file(user.uid)
            self.remove_schedule(user.uid)

            path = ''
            if user.deliver_voicenote:
                path = self.download_user_file(user)

            # Update/create database entry for logging and management
            self.create_db_schedule(user, path)
            self.logger.debug('Scheduled time: %s' % user.REMOVED.scheduled_date)

        self.scheduler_running = False
        self.logger.info("Finished handling downloads")

    def download_user_file(self, user: User):
        # Configure path
        filename = user.REMOVED.id + '.mp3'
        directory = self._get_download_dir() + user.uid
        path = os.path.join(directory, filename)

        # Create directory structure and download file
        req = requests.get(user.REMOVED.audio_url)
        self._create_directory(directory)
        with open(path, 'wb') as file:
            file.write(req.content)
        self.logger.debug('Downloaded file for user %s' % user.uid)
        return path

    def does_path_exist(self, path):
        return os.path.exists(path)

    def get_user_download_path(self, uid):
        return self._get_download_dir() + uid

    def delete_user_file(self, uid):
        self._delete_path(self._get_download_dir() + uid)

    def create_db_schedule(self, user: User, path):
        # Create download_collection object for insertion into database
        schedule = Schedule(user, path)

        # Insert object into downloads_collection and log database id
        try:
            schedule_id = self.downloads_collection.insert_one(schedule.__dict__).inserted_id
            self.logger.info('Schedule inserted in database with ID ' + str(schedule_id))
            return schedule_id
        except WriteError:
            self.logger.info('Entry exists for user %s & url %s' % (user.uid, user.REMOVED.audio_url))
            return None

    def remove_schedule(self, uid):
        self.downloads_collection.delete_many({"uid": uid})

    def get_schedule(self):
        schedule = self.downloads_collection.find({
            "delivered": False,
            "scheduled_millis": {
                "$lt": utils.time_in_millis_utc() + utils.MILLIS_1_HOUR,
                "$gt": utils.time_in_millis_utc()
            }})
        return schedule

    def mark_delivered(self, schedule):
        uid = schedule.uid
        REMOVED_id = schedule.id
        self.firebase.mark_REMOVED_delivered_now(uid, REMOVED_id)
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

    def get_overdue_schedules(self):
        return self.downloads_collection.find({"delivered": False,
                                               "scheduled_millis": {"$lt": utils.time_in_millis_utc()}
                                               })
