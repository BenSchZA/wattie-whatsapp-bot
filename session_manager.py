#!/usr/bin/env python3

import json
import threading
import log_manager
import uptime_manager

from selenium import webdriver
from selenium.webdriver.firefox.firefox_binary import FirefoxBinary
from selenium.common.exceptions import SessionNotCreatedException
from selenium.common.exceptions import NoSuchWindowException
from selenium.common.exceptions import WebDriverException
from urllib.error import URLError

TIMEOUT = 30

binary = FirefoxBinary('/usr/bin/firefox-developer-edition')
webdriver.DesiredCapabilities.FIREFOX["unexpectedAlertBehaviour"] = "accept"


class SessionManager:

    def __init__(self) -> None:
        super().__init__()

        log_manager.setup_logging()
        self.logger = log_manager.get_logger('session_manager')

        self.logger.info('Fetching Firefox session...')

        self.previous_session = {}
        self._fetch_session()

        self.driver = None
        if 'session' in self.previous_session:
            self.session = self.previous_session['session']
            self.session_id = self.session['session_id']
            self.executor_url = self.session['executor_url']

            self.logger.info('Session exists')
            self.logger.debug('Session ID: ' + self.session_id)

            self.driver = self._create_driver_session(self.session_id, self.executor_url)

        try:
            # If previous session does exist, reuse session
            self.driver.get('https://web.whatsapp.com/')
        except (SessionNotCreatedException, ConnectionRefusedError, URLError):
            # If previous session does not exist, create a new session
            self.logger.exception('Connection refused')
            self._create_new_driver_session()
        finally:
            uptime_manager.process_up(self)

    def _create_new_driver_session(self):
        self.logger.info('Creating new session...')
        driver = webdriver.Firefox(firefox_binary=binary)

        driver.get('https://web.whatsapp.com/')

        self.session_id = driver.session_id
        self.executor_url = driver.command_executor._url
        self._save_session(self.session_id, self.executor_url)

        self.logger.info('New session created')
        self.logger.debug('Session ID: ' + self.session_id)

        self.driver = driver

    def get_driver(self):
        return self.driver

    def _save_session(self, session_id, executer_url):
        self.previous_session = {'session': {
            'executor_url': executer_url,
            'session_id': session_id
        }}

        with open('session.data', 'w+') as outfile:
            json.dump(self.previous_session, outfile)

    def _fetch_session(self):
        try:
            with open('session.data') as json_file:
                self.previous_session = json.load(json_file)
        except FileNotFoundError:
            pass

    @staticmethod
    def _create_driver_session(session_id, executor_url):
        from selenium.webdriver.remote.webdriver import WebDriver as RemoteWebDriver

        capabilities = webdriver.DesiredCapabilities().FIREFOX.copy()
        capabilities["unexpectedAlertBehaviour"] = "accept"

        # Save the original function, so we can revert our patch
        org_command_execute = RemoteWebDriver.execute

        def new_command_execute(context, command, params=None):
            if command == "newSession":
                # Mock the response
                return {'success': 0, 'value': None, 'sessionId': session_id,
                        'capabilities': capabilities}
            else:
                return org_command_execute(context, command, params)

        # Patch the function before creating the driver object
        RemoteWebDriver.execute = new_command_execute

        new_driver = webdriver.Remote(command_executor=executor_url, desired_capabilities=capabilities)
        new_driver.session_id = session_id
        new_driver._is_remote = False

        # Replace the patched function with original function
        RemoteWebDriver.execute = org_command_execute

        return new_driver

    def connection_okay(self):
        try:
            return 'whatsapp' in self.driver.current_url
        except (WebDriverException, NoSuchWindowException):
            self.logger.exception("Connection okay exception")
            self.logger.critical("Connection down")
            return False

    def restart_connection(self):
        self.logger.info("Restarting connection")
        try:
            self.driver.quit()
        except SessionNotCreatedException:
            pass
        self.__init__()

    def monitor_connection(self):
            self.logger.info('Checking connection')

            self.logger.info('Uptime: ' + str(uptime_manager.get_uptime_percent(self)) + '%')

            active_connection = self.connection_okay()
            self.logger.debug("Active connection: " + str(active_connection))

            if not active_connection:
                self.restart_connection()
                uptime_manager.process_down(self)
            else:
                uptime_manager.process_up(self)

            threading.Timer(10, self.monitor_connection).start()


if __name__ == "__main__":
    # If you call this script from the command line (the shell) it will
    # run the 'main' function
    print("Starting Firefox session manager")
    session = SessionManager()
    print("Starting session monitor")
    session.monitor_connection()
    input("Press enter to exit - keep running for session to stay active\n")
