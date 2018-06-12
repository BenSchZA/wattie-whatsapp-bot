#!/usr/bin/env python3

import json
import threading
import log_manager
import uptime_manager
from schedule_manager import ScheduleManager
import time
import http_server
from multiprocessing import Process

from selenium import webdriver
from selenium.webdriver.firefox.firefox_binary import FirefoxBinary
from selenium.common.exceptions import SessionNotCreatedException
from selenium.common.exceptions import NoSuchWindowException
from selenium.common.exceptions import WebDriverException
from urllib.error import URLError

TIMEOUT = 30

binary = FirefoxBinary('/usr/bin/firefox-developer-edition')
webdriver.DesiredCapabilities.FIREFOX["unexpectedAlertBehaviour"] = "accept"

SESSION_DATA = 'data/session.data'
COOKIE_DATA = 'data/cookie.data'


class SessionManager:

    def __init__(self) -> None:
        super().__init__()

        # Start HTTP server in another process for service monitoring
        self.start_server()

        log_manager.setup_logging()
        self.logger = log_manager.get_logger('session_manager')

        self.schedule_manager = ScheduleManager()

        self.logger.info('Fetching Firefox session...')

        self.previous_session = {}
        self._fetch_session()

        self.cookies = {}

        self.driver = None
        if 'session' in self.previous_session:
            self.session = self.previous_session['session']
            self.session_id = self.session['session_id']
            self.executor_url = self.session['executor_url']

            self.logger.info('Session exists')
            self.logger.debug('Session ID: ' + self.session_id)

            self.driver = self._create_driver_session(self.session_id, self.executor_url)
        else:
            self._create_new_driver_session()

        try:
            # If previous session does exist, reuse session
            self.driver.get('https://web.whatsapp.com/')
            self._load_cookies()
            self.driver.get('https://web.whatsapp.com/')
        except (SessionNotCreatedException, ConnectionRefusedError, URLError):
            # If previous session does not exist, create a new session
            self.logger.exception('Connection refused', exc_info=False)
            self._create_new_driver_session()
        finally:
            uptime_manager.process_up(self)

    def start_server(self):
        # Start HTTP server in another process for service monitoring
        server_process = Process(target=http_server.run)
        server_process.start()

    def get_screenshot(self):
        self.wait_until_connection_okay()
        time.sleep(5)
        return self.driver.get_screenshot_as_png()

    def _create_new_driver_session(self):
        self.logger.info('Creating new session...')
        self.driver = webdriver.Firefox(firefox_binary=binary)

        self.driver.get('https://web.whatsapp.com/')
        self._load_cookies()
        self.driver.get('https://web.whatsapp.com/')

        self.logger.info('New session created')
        self.logger.debug('Session ID: ' + self.session_id)

        self.session_id = self.driver.session_id
        self.executor_url = self.driver.command_executor._url
        self._save_session(self.session_id, self.executor_url)

    def get_driver(self):
        return self.driver

    def _save_session(self, session_id, executer_url):
        self.previous_session = {'session': {
            'executor_url': executer_url,
            'session_id': session_id
        }}

        with open(SESSION_DATA, 'w+') as outfile:
            json.dump(self.previous_session, outfile)

    def _fetch_session(self):
        try:
            with open(SESSION_DATA) as json_file:
                self.previous_session = json.load(json_file)
        except FileNotFoundError:
            pass

    def save_cookies(self):
        cookies = self.driver.get_cookies()
        for cookie in cookies:
            self.logger.debug('Saving cookie: ' + cookie)
        self.cookies = {'cookies': cookies}

        with open(COOKIE_DATA, 'w+') as outfile:
            json.dump(self.cookies, outfile)

    def _load_cookies(self):
        try:
            with open(COOKIE_DATA) as json_file:
                data = json.load(json_file)
                if 'cookies' in data:
                    self.cookies = data
                    for key, value in self.cookies['cookies'].items():
                        self.driver.add_cookie({'name': key, 'value': value, 'path': '/pp',
                                                'domain': '.web.whatsapp.com', 'secure': True})
        except (FileNotFoundError, NoSuchWindowException):
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

    def wait_until_connection_okay(self):
        must_end = time.time() + TIMEOUT
        while time.time() < must_end:
            if self.connection_okay():
                return True
            time.sleep(0.5)
        return False

    def restart_connection(self):
        self.logger.info("Restarting connection")
        try:
            self.driver.quit()
        except SessionNotCreatedException:
            pass
        self.__init__()

    def refresh_connection(self):
        self.logger.info("Refreshing connection")
        try:
            self.driver.refresh()
        except SessionNotCreatedException:
            pass

    def monitor_connection(self):
            self.logger.info('Checking connection')

            self.logger.info('Uptime: ' + str(int(round(uptime_manager.get_uptime_percent(self)))) + '%')

            active_connection = self.connection_okay()
            self.logger.debug("Active connection: %r" % active_connection)
            self.logger.debug("Handler running: %r" % self.schedule_manager.handler_running)

            if not active_connection:
                # self.server.set_response(self.server(), 500)
                self.restart_connection()
                uptime_manager.process_down(self)
            else:
                uptime_manager.process_up(self)
                # Process scheduled deliveries
                if not self.schedule_manager.handler_running:
                    self.schedule_manager.handle_schedules()

            threading.Timer(10, self.monitor_connection).start()


if __name__ == "__main__":
    # If you call this script from the command line (the shell) it will
    # run the 'main' function
    print("Starting Firefox session manager")
    session = SessionManager()
    print("Starting session monitor")
    session.monitor_connection()
    input("Press enter to exit - keep running for session to stay active\n")
