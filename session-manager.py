import json

from selenium import webdriver
from selenium.webdriver.firefox.firefox_binary import FirefoxBinary

TIMEOUT = 30

binary = FirefoxBinary('/usr/bin/firefox-developer-edition')
webdriver.DesiredCapabilities.FIREFOX["unexpectedAlertBehaviour"] = "accept"

driver = webdriver.Firefox(firefox_binary=binary)
driver.implicitly_wait(TIMEOUT)


class SessionManager:

    def __init__(self) -> None:
        super().__init__()

        self.previous_session = {}
        self.previous_session['session'].append({
            'executor_url': '',
            'session_id': ''
        })

        self._fetch_session()

        self.driver = None
        if 'session' in self.previous_session:
            self.session_id = self.previous_session['session_id']
            self.executor_url = self.previous_session['executor_url']

            self.driver = self._create_driver_session(self.session_id, self.executor_url)

        if not self.driver:
            # If previous session does not exist, create a new session
            driver.get('https://web.whatsapp.com/')

            self.session_id = driver.session_id
            self.executor_url = driver.command_executor._url
            self._save_session(self.session_id, self.executor_url)

            self.driver = driver
        else:
            # If previous session does exist, reuse session
            self.driver.get('https://web.whatsapp.com/')

    def get_driver(self):
        return self.driver

    def _save_session(self, session_id, executer_url):
        self.previous_session['session'].append({
            'executor_url': executer_url,
            'session_id': session_id
        })

        with open('session.txt', 'w') as outfile:
            json.dump(self.previous_session, outfile)

    def _fetch_session(self):
        with open('session.txt') as json_file:
            self.previous_session = json.load(json_file)

    @staticmethod
    def _create_driver_session(session_id, executor_url):
        from selenium.webdriver.remote.webdriver import WebDriver as RemoteWebDriver

        # Save the original function, so we can revert our patch
        org_command_execute = RemoteWebDriver.execute

        def new_command_execute(context, command, params=None):
            if command == "newSession":
                # Mock the response
                return {'success': 0, 'value': None, 'sessionId': session_id}
            else:
                return org_command_execute(context, command, params)

        # Patch the function before creating the driver object
        RemoteWebDriver.execute = new_command_execute

        new_driver = webdriver.Remote(command_executor=executor_url, desired_capabilities={})
        new_driver.session_id = session_id

        # Replace the patched function with original function
        RemoteWebDriver.execute = org_command_execute

        return new_driver
