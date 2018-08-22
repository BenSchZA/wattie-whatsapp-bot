#!/usr/bin/env python3

import json
import threading
import log_manager
import uptime_manager
import time
from multiprocessing import Process
from retrying import retry
import os
import utils
import alert_manager

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import SessionNotCreatedException
from selenium.common.exceptions import NoSuchWindowException
from selenium.common.exceptions import WebDriverException
from selenium.common.exceptions import NoAlertPresentException
from selenium.common.exceptions import UnexpectedAlertPresentException
from selenium.common.exceptions import NoSuchElementException
from urllib3.exceptions import NewConnectionError, MaxRetryError
from urllib.error import URLError

from celery_config import app as celery_app
from celery_config import Queues

SESSION_DATA = 'data/session.data'
COOKIE_DATA = 'data/cookie.data'

firefox_profile = webdriver.FirefoxProfile()
firefox_profile.set_preference('permissions.default.image', 2)
firefox_profile.set_preference('dom.ipc.plugins.enabled.libflashplayer.so', 'false')


class SessionManager:

    def __init__(self) -> None:
        super().__init__()

        # Configure logging
        log_manager.setup_logging()
        self.logger = log_manager.get_logger('session_manager')

        # Initialize session variables
        self.logger.info(utils.whos_calling('Fetching Firefox session...'))
        self.previous_session = self._fetch_previous_session()
        self.active_browser_connection = False
        self.cookies = {}
        self.driver = None

        # Try reuse previous persisted session
        if 'session' in self.previous_session:
            self.session = self.previous_session['session']
            self.session_id = self.session['session_id']
            self.executor_url = self.session['executor_url']

            self.logger.info('Fetching driver session with ID: %s' % self.session_id)
            self.driver = SessionManager.get_existing_driver_session()
        else:
            self._create_new_driver_session()
        self.logger.debug('Using session with ID: %s' % self.driver.session_id)

        """
        Try load webpage - if this fails, then session is invalid
        * If previous session exists, reuse session
        * If previous session does not exist, create a new session
        """
        self.logger.info('Starting WhatsApp web')
        try:
            self.driver.get('https://web.whatsapp.com/')
            self.monitor_connection()
            # self._load_cookies()
            # self.driver.get('https://web.whatsapp.com/')
        except (WebDriverException, SessionNotCreatedException,
                ConnectionRefusedError, URLError, NewConnectionError, MaxRetryError):
            self.logger.exception('Connection refused', exc_info=False)
            self._create_new_driver_session()
            self.monitor_connection()
        finally:
            uptime_manager.process_up(self)

        # Start API & service monitoring
        self.start_api()

    def start_api(self):
        self.logger.info('Starting API')
        import api
        # Start HTTP server in another process for API service monitoring
        try:
            api_process = Process(target=api.start)
            api_process.start()
            self.logger.info('API started')
        except OSError:
            self.logger.error('API error')
            pass

    @staticmethod
    def get_screenshot():
        # Get screenshot of current browser session
        SessionManager.wait_until_connection_okay()
        time.sleep(5)
        driver = SessionManager.get_existing_driver_session()
        if driver:
            return driver.get_screenshot_as_png()
        else:
            return None

    @retry(wait_exponential_multiplier=500, wait_exponential_max=60000)
    def _create_new_driver_session(self):
        self.logger.info('Creating new session...')

        capabilities = webdriver.DesiredCapabilities().FIREFOX.copy()
        capabilities["unexpectedAlertBehaviour"] = "accept"

        self.driver = webdriver.Remote(command_executor='http://hub:4444/wd/hub',
                                       desired_capabilities=capabilities)
        # browser_profile=firefox_profile,
        # self.driver = webdriver.Firefox(firefox_binary=binary)

        self.driver.get('https://web.whatsapp.com/')
        # self._load_cookies()
        # self.driver.get('https://web.whatsapp.com/')

        self.session_id = self.driver.session_id
        self.executor_url = self.driver.command_executor._url

        self.logger.info('New session created')
        self.logger.debug('Session ID: ' + self.session_id)

        self._save_session(self.session_id, self.executor_url)

    def _save_session(self, session_id, executer_url):
        self.previous_session = {'session': {
            'executor_url': executer_url,
            'session_id': session_id
        }}

        with open(SESSION_DATA, 'w+') as outfile:
            json.dump(self.previous_session, outfile)

    def _fetch_previous_session(self):
        try:
            with open(SESSION_DATA) as json_file:
                return json.load(json_file)
        except FileNotFoundError:
            return {}

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
    def get_existing_driver_session():
        previous_session = {}
        try:
            with open(SESSION_DATA) as json_file:
                previous_session = json.load(json_file)
        except FileNotFoundError:
            pass

        if 'session' in previous_session:
            session_id = previous_session['session']['session_id']
            executor_url = previous_session['session']['executor_url']
            return SessionManager._get_existing_driver_session(session_id, executor_url)
        else:
            return None

    @staticmethod
    def _get_existing_driver_session(session_id, executor_url):
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

        new_driver = webdriver.Remote(
            command_executor=executor_url,
            desired_capabilities=capabilities)
        # browser_profile=firefox_profile,
        new_driver.session_id = session_id
        new_driver._is_remote = True

        # Replace the patched function with original function
        RemoteWebDriver.execute = org_command_execute

        return new_driver

    def browser_connection_okay(self):
        try:
            return 'whatsapp' in self.driver.current_url
        except (WebDriverException, NoSuchWindowException):
            self.logger.exception("Connection okay exception")
            self.logger.critical("Connection down")
            return False

    @staticmethod
    def wait_until_connection_okay():
        time_limit = time.time() + int(os.environ['TIMEOUT'])

        driver = SessionManager.get_existing_driver_session()
        wait = WebDriverWait(driver, int(os.environ['TIMEOUT']))

        while time.time() < time_limit:
            if 'whatsapp' in driver.current_url\
                    and wait.until(lambda _: driver.find_element_by_xpath("//div[@class='_3q4NP _1Iexl']")):
                return True
            time.sleep(0.5)
        return False

    @staticmethod
    def whatsapp_web_connection_okay():
        try:
            driver = SessionManager.get_existing_driver_session()
            driver.find_element_by_xpath("//div[@class='_3q4NP _1Iexl']")
            return 'whatsapp' in driver.current_url
        except NoSuchElementException:
            return False

    def restart_connection(self):
        self.logger.info("Restarting connection")
        try:
            self.driver.quit()
        except SessionNotCreatedException:
            pass
        self.__init__()

    def refresh_connection_else_restart(self):
        try:
            driver = SessionManager.get_existing_driver_session()
            if driver:
                # Disable alert dialog before starting
                driver.execute_script("window.onbeforeunload = function(e){};")
                try:
                    driver.refresh()
                except UnexpectedAlertPresentException:
                    try:
                        driver.switch_to.alert.dismiss()
                    except NoAlertPresentException:
                        pass
        except (SessionNotCreatedException, NoAlertPresentException):
            self.restart_connection()

    @staticmethod
    def refresh_connection():
        try:
            driver = SessionManager.get_existing_driver_session()
            if driver:
                # Disable alert dialog before starting
                driver.execute_script("window.onbeforeunload = function(e){};")
                try:
                    driver.refresh()
                except UnexpectedAlertPresentException:
                    try:
                        driver.switch_to.alert.dismiss()
                    except NoAlertPresentException:
                        pass
        except (SessionNotCreatedException, NoAlertPresentException):
            pass

    def toggle_celery_consumer_state(self):
        """
        Enable and disable Celery consumers for Selenium task queue
        * If WhatsApp web is operating, enable queue
        """
        active_whatsapp_connection = self.whatsapp_web_connection_okay()
        with celery_app.connection_or_acquire() as conn:
            if not active_whatsapp_connection:
                # For each queue, remove consumer
                for queue in Queues:
                    # If download queue, ignore
                    if Queues(queue).name == Queues.download.name:
                        continue
                    reply = celery_app.control.cancel_consumer(Queues(queue).name, connection=conn, reply=True,
                                                               destination=['celery@worker_q_selenium'])
                    self.logger.debug(reply)
            else:
                # For each queue, add consumer
                for queue in Queues:
                    # If download queue, ignore
                    if Queues(queue).name == Queues.download.name:
                        continue
                    reply = celery_app.control.add_consumer(Queues(queue).name, connection=conn, reply=True,
                                                            destination=['celery@worker_q_selenium'])
                    self.logger.debug(reply)

    def monitor_connection(self):
            self.active_browser_connection = self.browser_connection_okay()
            self.logger.info('Connection: Uptime ~ %s; Active ~ %s'
                             % (str(int(round(uptime_manager.get_uptime_percent(self))))
                                + '%', self.active_browser_connection))

            if not self.active_browser_connection:
                self.refresh_connection_else_restart()
                uptime_manager.process_down(self)
            else:
                uptime_manager.process_up(self)

            self.toggle_celery_consumer_state()

            threading.Timer(int(os.environ['MONITOR_FREQUENCY']), self.monitor_connection).start()


if __name__ == "__main__":
    log_manager.setup_logging()
    logger = log_manager.get_logger('session_manager')
    logger.debug(utils.whos_calling("Starting session manager"))

    # If Docker environment variable set to True, then enable debugger
    if os.environ.get('ENABLE_DEBUG', False) is True:
        import ptvsd
        # Allow other computers to attach to ptvsd at this IP address and port, using the secret
        ptvsd.enable_attach("secret", address=('0.0.0.0', 5050))
        # Pause the program until a remote debugger is attached
        logger.debug("Waiting for debugger to attach...")
        ptvsd.wait_for_attach()
        logger.debug("Debugger attached")

    # Clear pending Celery tasks, for fresh start
    import tasks
    tasks.purge_tasks()

    session = SessionManager()
    alert_manager = alert_manager.AlertManager()
    alert_manager.slack_alert('Wattie session started')
