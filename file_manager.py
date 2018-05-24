import os
import errno
import urllib.request
from urllib.parse import urlparse
import time
import datetime
from pymongo import MongoClient
import log_manager

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

        self.downloads_collection = self.db.downloads_collection

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

    def download_from_url(self, uid, url, subfolder):
        # Parse url and create path for download
        parsed = urlparse(url)
        filename = os.path.basename(parsed.path)
        directory = DOWNLOADS + '/' + subfolder
        path = os.path.join(directory, filename)

        # Create directory structure and download file
        self._create_directory(directory)
        urllib.request.urlretrieve(url, path)

        # Create database entry for logging and management
        self._log_download(uid, url, path)
        return path

    def _log_download(self, uid, url, path):
        # Create download_collection object for insertion into database
        created = time.ctime()
        delivered = False
        download = {
            'uid': uid,
            'url': url,
            'path': path,
            'delivered': delivered,
            'created_millis': created,
            'created_date': datetime.datetime.utcnow()
        }

        # Insert object into downloads_collection and log database uid
        download_id = self.downloads_collection.insert_one(download).inserted_id
        self.logger.info('File downloaded & stored in database with ID ' + str(download_id))
        return download_id
