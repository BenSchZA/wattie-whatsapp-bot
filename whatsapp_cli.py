#!/usr/bin/env python3

import argparse
import os
import sys
import time

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as exp_c
from selenium.webdriver.common.by import By
from selenium.common.exceptions import *
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.keys import Keys

from session_manager import SessionManager
from message import Message

TIMEOUT = 30
# TIMEOUT = os.environ['TIMEOUT']


class WhatsAppCli:

    def __init__(self) -> None:
        super().__init__()

        self.session = SessionManager
        self.driver = self.session.get_existing_driver_session()
        self.wait = WebDriverWait(self.driver, TIMEOUT)

        self.number = None
        self.txt = None
        self.media = None
        self.url = None

    def _handle_alert(self):
        print("Handling alert")
        try:
            # Disable alert dialog before starting
            self.driver.execute_script("window.onbeforeunload = function(e){};")
            alert = self.driver.switch_to.alert
            alert.accept()
        except NoAlertPresentException as e:
            print(str(e))
            pass

    def try_search_for_contact(self, contact_number):
        # Enter search text
        try:
            search_bar = WebDriverWait(self.driver, TIMEOUT).until(
                exp_c.visibility_of_element_located((By.XPATH, "//input[@class='jN-F5 copyable-text selectable-text']"))
            )
            search_bar.click()
            search_bar.send_keys(contact_number)
            print('Searching for contact ' + contact_number)
        except (ElementClickInterceptedException, TimeoutException):
            return False
        # Wait for finished loading
        try:
            clear_search = self.wait.until(lambda _: self.driver.find_element_by_xpath("//button[@class='_3Burg']"))
        except TimeoutException:
            return False
        # If no contacts found, return False
        try:
            self.driver.find_element_by_xpath("//div[@class='_3WZoe']")
            print('No contacts found')
            return False
        except NoSuchElementException:
            print('Contact found')
            pass
        # Else Press enter
        try:
            if search_bar:
                print('Selecting contact conversation')
                search_bar.send_keys(Keys.RETURN)
                clear_search.click()
        except ElementClickInterceptedException:
            return False
        # Check contact header for correct number
        try:
            print('Waiting for contact header')
            contact_header = self.wait.until(lambda _: self.driver.find_element_by_xpath("//header[@class='_3AwwN']"))
        except TimeoutException:
            return False
        try:
            print('Fetching contact ID')
            contact_id = self.wait.until(lambda _: contact_header.find_element_by_xpath(".//span[@class='_1wjpf']")) \
                .get_attribute('title')
        except TimeoutException:
            return False

        print('Contact ID %s ~ Contact number %s' % (contact_id, contact_number))
        if contact_id and contact_number and (contact_id.replace(" ", "").replace("+", "")
                                              == contact_number.replace(" ", "").replace("+", "")):
            return True
        else:
            return False

    def _process_queue(self):
        print("Processing queue...")

        processed_message = False
        processed_url = False
        processed_media = False

        print('Ensuring connection okay')
        self.session.wait_until_connection_okay()

        print('Processing number ' + self.number)

        # Try search for number before using WhatsApp API - the latter is slower
        if not self.try_search_for_contact(self.number):
            contact_header = None
            try:
                contact_header = self.driver.find_element_by_xpath("//header[@class='_3AwwN']")
            except NoSuchElementException:
                pass

            # If no contact open, load contact, else load next contact and wait for staleness of present contact
            if not contact_header:
                print('Contact header not present: fetching')
                self.driver.get('https://web.whatsapp.com/send?phone=' + self.number)
            else:
                print('Contact header present: refreshing')
                try:
                    self.driver.get('https://web.whatsapp.com/send?phone=' + self.number)
                    WebDriverWait(self.driver, TIMEOUT).until(
                        exp_c.staleness_of(contact_header)
                    )
                except TimeoutException:
                    self.session.refresh_connection()
                    exit(1)
                finally:
                    print('Page refreshed')

        if self.txt:
            try:
                content = WebDriverWait(self.driver, TIMEOUT).until(
                    exp_c.visibility_of_element_located((By.XPATH, "//div[@contenteditable='true']"))
                )
                content.click()
                content.send_keys(self.txt)
                print('Sending message to ' + self.number)
            except (ElementClickInterceptedException, TimeoutException):
                self.session.refresh_connection()
                exit(1)
            finally:
                pass

            try:
                send_button = WebDriverWait(self.driver, TIMEOUT).until(
                    exp_c.visibility_of_element_located((By.CLASS_NAME, "_35EW6"))
                )
                send_button.click()
                print('Message sent to ' + self.number)
            except (ElementClickInterceptedException, TimeoutException):
                self.session.refresh_connection()
                exit(1)
            finally:
                processed_message = True
                pass

        if self.url:
            try:
                content = WebDriverWait(self.driver, TIMEOUT).until(
                    exp_c.visibility_of_element_located((By.XPATH, "//div[@contenteditable='true']"))
                )
                content.click()
                content.send_keys(self.url)
                print('Sending url to ' + self.number)
            except (ElementClickInterceptedException, TimeoutException):
                self.session.refresh_connection()
                exit(1)
            finally:
                pass

            try:
                send_button = WebDriverWait(self.driver, TIMEOUT).until(
                    exp_c.visibility_of_element_located((By.CLASS_NAME, "_35EW6"))
                )
                send_button.click()
                print('Url sent to ' + self.number)
            except (ElementClickInterceptedException, TimeoutException):
                self.session.refresh_connection()
                exit(1)
            finally:
                processed_url = True
                pass

        if self.media:
            try:
                attach = WebDriverWait(self.driver, TIMEOUT).until(
                    exp_c.visibility_of_element_located((By.XPATH, "//div[@title='Attach']"))
                )
                attach.click()
                print('Attaching file for ' + self.number)
            except (ElementClickInterceptedException, TimeoutException):
                self.session.refresh_connection()
                exit(1)
            finally:
                pass

            try:
                file = self.driver.find_element_by_xpath("//input[@accept='*']")
                self.driver.execute_script("arguments[0].style.display='block';", file)
                WebDriverWait(self.driver, TIMEOUT).until(
                    exp_c.visibility_of(file)
                )
                file.send_keys(self.media)
                print('File attached for ' + self.number)
            except (ElementClickInterceptedException, TimeoutException):
                self.session.refresh_connection()
                exit(1)
            finally:
                pass

            try:
                print('Sending attachment to ' + self.number)
                send_file = WebDriverWait(self.driver, TIMEOUT).until(
                    exp_c.visibility_of_element_located((By.XPATH, "//div[@class='_3hV1n yavlE']"))
                )
                send_file.click()
                print('Waiting for attachment to upload')
                WebDriverWait(self.driver, TIMEOUT).until(
                    exp_c.visibility_of_element_located((By.XPATH, "//div[@class='_3SUnz']"))
                )
                WebDriverWait(self.driver, TIMEOUT*10).until(
                    exp_c.invisibility_of_element_located((By.XPATH, "//div[@class='_3SUnz']"))
                )
                print('Attachment sent to ' + self.number)
            except (ElementClickInterceptedException, TimeoutException):
                self.session.refresh_connection()
                exit(1)
            finally:
                processed_media = True
                pass
        if (self.txt and not processed_message) or (self.url and not processed_url) or (self.media and not processed_media):
            exit(1)
        else:
            exit(0)

    def send_message(self, message: Message):
        self.number = message.number
        self.txt = message.txt
        self.media = message.media
        self.url = message.url

        return self.process_and_handle_alerts()

    def process_and_handle_alerts(self):
        limit = 5
        delay = 1000
        for _ in range(0, limit):
            while True:
                try:
                    # Disable alert dialog before starting
                    self.driver.execute_script("window.onbeforeunload = function(e){};")

                    self._process_queue()
                except UnexpectedAlertPresentException as e:
                    print("UnexpectedAlertPresentException: " + str(e))
                    # Attempt to clear content in case that was the cause of alert
                    try:
                        content = WebDriverWait(self.driver, 5).until(
                            exp_c.visibility_of_element_located((By.XPATH, "//div[@contenteditable='true']"))
                        )
                        content.clear()
                        print("Content cleared")
                    except TimeoutException:
                        pass
                    self._handle_alert()
                    time.sleep(delay/1000)
                    continue
                exit(0)
                break
        exit(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('--number', help='to number', required=True)
    parser.add_argument('--txt', help='send message', type=str, required=False)
    parser.add_argument('--media', help='media attachment', type=str, required=False)
    parser.add_argument('--url', help='url link', type=str, required=False)

    args = parser.parse_args()

    cli = WhatsAppCli()

    cli.number = args.number
    cli.txt = args.txt
    cli.media = args.media
    cli.url = args.url

    cli.process_and_handle_alerts()
