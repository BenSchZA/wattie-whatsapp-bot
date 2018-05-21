import os
import errno


class FileManager:
    
    def __init__(self) -> None:
        super().__init__()
        self._initialize_directories()

    def _initialize_directories(self):
        self._create_directory('logs')
        self._create_directory('downloads')

    @staticmethod
    def _create_directory(directory):
        try:
            os.makedirs(directory)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise
