#!/usr/bin/env python3

import time
import datetime
import dateutil.parser
from difflib import SequenceMatcher

from selenium import webdriver
from selenium.webdriver.firefox.firefox_binary import FirefoxBinary

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as exp_c
from selenium.webdriver.common.by import By
from selenium.common.exceptions import *
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.keys import Keys

import pymongo
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.errors import WriteError

from session_manager import SessionManager
from whatsapp_message import WhatsAppMessage
import re
import requests
import os

TIMEOUT = 60
MESSAGE_LIMIT = 5

binary = FirefoxBinary('/usr/bin/firefox-developer-edition')
webdriver.DesiredCapabilities.FIREFOX["unexpectedAlertBehaviour"] = "accept"


class WhatsAppProcess:

    def __init__(self) -> None:
        super().__init__()

        self._initialize_database()

        self.session = SessionManager
        self.driver = self.session.get_existing_driver_session()

        # self.driver = webdriver.Firefox(firefox_binary=binary)
        # self.driver.get('https://web.whatsapp.com/')

        self.wait = WebDriverWait(self.driver, TIMEOUT)

        self.processed_conversation_ids = []
        self.previous_conversation_content = None

        self.processed_contacts = []

    def _initialize_database(self):
        self.client = MongoClient('localhost', 27017)
        self.db = self.client.whatsapp_cli

        # MongoDB scales horizontally, so: single messages collection containing all messages from all conversations
        self.messages_collection: Collection = self.db.messages
        self.messages_collection.create_index([("uid", pymongo.DESCENDING), ("timestamp", pymongo.DESCENDING),
                                               ("content", pymongo.DESCENDING)], unique=True)

    def process_new_users(self):
        self._for_each_conversation(self._process_contact)
        print(self.processed_contacts)

        new_user_contacts = self._get_new_user_contacts()
        print(new_user_contacts)

        print('Checking for new users')
        if not new_user_contacts:
            break
        for number in new_user_contacts:
            if self.try_search_for_contact(number):
                # conversation = self._find_conversation_by_id(number)
                # self._process_conversation(conversation)
                messages_panel = self.wait.until(lambda _: self.driver.find_element_by_xpath("//div[@class='_9tCEa']"))
                username = self._process_new_user(messages_panel)
                if username:
                    print('New user %s ~ %s' % (username, number))
                    new_uid = self._create_new_user(contact_number=number, username=username)
                    if new_uid:
                        print('Successfully created user: %s' % new_uid)
                    else:
                        print('Failed to create user: %s' % number)
                        continue
                else:
                    print('No valid launch sequence for %s' % number)
                    continue
                new_user_contacts.remove(number)
            else:
                print('Couldnt find contact')

        # self.processed_contacts = list(map(lambda contact: self._clean_contact_number(contact), self.processed_contacts))
        # self.processed_contacts = list(filter(None.__ne__, self.processed_contacts))
        #
        # for number in self.processed_contacts:
        #     print('Number: %s _ %s' % (number, self._get_uid_from_number(number)))
        # print(self.processed_contacts)

    def _get_new_user_contacts(self):
        new_user_contacts = []
        for number in self.processed_contacts:
            uid = self.get_uid_from_number_db(number)
            if uid:
                print('Existing user: %s' % uid)
                continue
            else:
                uid = self._get_uid_from_number(number)
            if not uid:
                print('New user: %s' % number)
                new_user_contacts.append(number)
        return new_user_contacts

    def _clean_contact_number(self, contact_number):
        contact_number = contact_number.replace(' ', '')
        if self._is_valid_numeric(contact_number):
            return contact_number
        else:
            return None

    def _is_valid_numeric(self, string):
        for char in string:
            if char.isdigit() or char == '+':
                continue
            else:
                return False
        return True

    def _get_uid_from_number(self, contact_number):
        data = {
            'content-type': 'application/json',
            'fullMobileNum': contact_number
        }

        headers = {
            'Authorization': '56128eebf5a64cb6875b8d1c4789b216cf2331aa',
            'Origin': 'https://my***REMOVED***.com'
        }

        req = requests.post("***REMOVED***:3000/user_uid_from_full_mobile_num", data=data, headers=headers)

        if req.status_code == 200:
            return req.json()['userUID']
        else:
            print(req.status_code, req.reason)
            return None

    def _create_new_user(self, contact_number, username=None):
        data = {
            'Content-Type': 'application/json',
            'fullMobileNum': contact_number,
            'username': username
        }

        headers = {
            'Authorization': '***REMOVED***',
            'Origin': 'http://my***REMOVED***.com'
        }

        req = requests.post("http://***REMOVED***-client-api.fzg22nmp77.us-east-2.elasticbeanstalk.com/users/create_user_full_num", data=data, headers=headers)

        if req.status_code == 200:
            return req.json()['userUID']
        else:
            print(req.status_code, req.reason)
            return None

    def process_messages(self):
        self._for_each_conversation(self._process_conversation)

    def _for_each_conversation(self, func):
        print('Ensuring connection okay')
        # self.session.wait_until_connection_okay()

        print('Fetching conversations panel')
        conversations_panel: WebElement = self._get_conversations_panel()
        print('Fetching conversations')
        conversations: [WebElement] = lambda: conversations_panel.find_elements_by_class_name('_2wP_Y')

        print('Processing conversations')
        while True:
            def sorted_conversations(): return sorted(conversations(), key=lambda el: self._get_element_y_position(el))
            conversations_copy = sorted_conversations().copy()
            # print(list(map(lambda conv: '%s ~ %s' % (conv.id, conv.text), conversations_copy)))
            for index in range(len(conversations_copy)):
                func(conversations_copy[index])

            scroll_progress = self._side_pane_scroll_top()
            scroll_max = self._side_pane_scroll_top_max()
            if scroll_progress == scroll_max:
                break

            last_processed_conversation = conversations_copy[-1]
            self._scroll_into_view(last_processed_conversation, True)
            time.sleep(0.1)

            progress = round((scroll_progress/scroll_max)*100)
            print('Progress: %s' % progress)

    def _process_contact(self, conversation: WebElement):
        contact_name_number = self.wait.until(lambda _: conversation.find_element_by_xpath(".//span[@class='_1wjpf']")) \
            .get_attribute('title')

        if contact_name_number not in self.processed_contacts:
            self.processed_contacts.append(contact_name_number)

        return contact_name_number

    def _process_conversation(self, conversation: WebElement):
        print('\nProcessing conversation...')
        uid = None
        try:
            # Assuming the user is not saved as a contact, 'contact_id' will return the number
            contact_id = self.wait.until(lambda _: conversation.find_element_by_xpath(".//span[@class='_1wjpf']")) \
                .get_attribute('title')

            contact_id = self._clean_contact_number(contact_id)
            if not contact_id:
                print('Invalid contact ID')
                return False

            # Try get uid from local database, otherwise perform network call,
            # if this fails then user needs to be created first
            uid = self.get_uid_from_number_db(contact_id)
            if not uid:
                uid = self._get_uid_from_number(contact_id)
            if not uid:
                print('User needs to be created')

            last_message_content = self.wait.until(lambda _: conversation.find_element_by_xpath(".//span[@class='_2_LEW']")) \
                .get_attribute('title')

            last_message = WhatsAppMessage(uid=uid, timestamp=None, sender_name=None, sender_number=contact_id, content=last_message_content)
            del last_message.timestamp
            del last_message.sender_name

            if self.messages_in_sync(last_message):
                print('Messages in sync')
                return True

            print('Processing conversation %s: ID - %s' % (conversation.id, contact_id))
        except NoSuchElementException:
            print('No such element')
            return False

        messages_panel = self.load_conversation_messages_panel(conversation)
        self.previous_conversation_content = messages_panel

        if uid:
            # messages = self._extract_and_save_messages(messages_panel)
            # print('Saving messages to database')
            # for message in messages:
            #     message.uid = uid
            #     self.save_message(message)
            #     print('Message: %s' % message.__dict__)
            return True
        else:
            username = self._process_new_user(messages_panel)
            if username:
                print('New user %s ~ %s' % (username, contact_id))
                new_uid = self._create_new_user(contact_number=contact_id, username=username)
                if new_uid:
                    print('Successfully created user: %s' % new_uid)
                else:
                    print('Failed to create user: %s' % contact_id)
            else:
                print('No valid launch sequence for %s' % contact_id)
            return False

    def load_conversation_messages_panel(self, conversation):

        self.wait.until(lambda _: conversation and conversation.is_displayed() and conversation.is_enabled())
        while True:
            try:
                conversation.click()
                break
            except ElementClickInterceptedException:
                time.sleep(0.1)
                continue

        # If moving from active conversation, wait for content to refresh after click
        # while True:
        #     self.wait.until(lambda _: conversation and conversation.is_displayed() and conversation.is_enabled())
        #     conversation.click()
        #     try:
        #         conversation.click()
        #         break
        #     except ElementClickInterceptedException:
        #         self._scroll_into_view(conversation, False)
        #         continue

        if self.previous_conversation_content:
            self.wait.until(exp_c.staleness_of(self.previous_conversation_content))

        messages_panel = self.wait.until(lambda _: conversation.find_element_by_xpath("//div[@class='_9tCEa']"))
        # self.wait.until(
        #     lambda _: 'loading' not in messages_panel.find_element_by_class_name('_3dGYA').get_attribute('title'))

        # Scroll through all messages until 100 messages are scraped, or we reach the top
        try:
            while len(messages_panel.find_elements_by_class_name('vW7d1')) < MESSAGE_LIMIT:
                try:
                    load_spinner = WebDriverWait(self.driver, 2) \
                        .until(lambda _: self.driver.find_element_by_xpath("//div[@class='_3dGYA']"))
                    self._scroll_into_view(load_spinner, True)
                except (TimeoutException, StaleElementReferenceException):
                    break
                self.wait.until(lambda _: not self._messages_are_loading())
        except NoSuchElementException:
            pass

        return messages_panel

    def _scroll_into_view(self, web_element, align_top: bool):
        return self.driver.execute_script('return arguments[0].scrollIntoView(%s);' % 'true' if align_top else 'false', web_element)

    def _get_element_y_position(self, web_element):
        return self.driver.execute_script('return arguments[0].getBoundingClientRect().top;', web_element)

    def _scroll_top(self, web_element):
        return self.driver.execute_script('return arguments[0].scrollTop;', web_element)

    def _scroll_top_max(self, web_element):
        return self.driver.execute_script('return arguments[0].scrollTopMax;', web_element)

    def _side_pane_scroll_top(self):
        side_pane = self.driver.find_element_by_id('pane-side')
        return self._scroll_top(side_pane)

    def _side_pane_scroll_top_max(self):
        side_pane = self.driver.find_element_by_id('pane-side')
        return self._scroll_top_max(side_pane)

    def _side_pane_scroll_by(self, pixels):
        side_pane = self.driver.find_element_by_id('pane-side')
        return self.driver.execute_script('return arguments[0].scrollBy(0, %d);' % pixels, side_pane)

    def _side_pane_scroll_to(self, pixels):
        side_pane = self.driver.find_element_by_id('pane-side')
        return self.driver.execute_script('return arguments[0].scrollTo(0, %d);' % pixels, side_pane)

    def _messages_are_loading(self):
        try:
            def load_spinner(): self.driver.find_element_by_xpath("//div[@class='_3dGYA']")
            if load_spinner():
                return 'loading' in load_spinner().get_attribute('title')
            else:
                return False
        except NoSuchElementException:
            return False

    def _get_conversations_panel(self):
        conversations_panel = None
        try:
            conversations_panel = self.wait.until(
                exp_c.visibility_of_element_located((By.XPATH, "//div[@class='RLfQR']")))
        except TimeoutException:
            pass
        return conversations_panel

    def _find_conversation_by_id(self, contact_id):
        conversations_panel: WebElement = self._get_conversations_panel()
        try:
            return conversations_panel.find_element_by_xpath(".//span[@class='_1wjpf'][@title='%s']/ancestor::div[@class='_2wP_Y']" % contact_id)
        except NoSuchElementException:
            return None

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

    def _extract_and_save_messages(self, messages_panel):
        messages: [WhatsAppMessage] = []

        def append_message(message): messages.append(message)
        self._for_each_message(messages_panel, append_message)

        return messages

    def _process_new_user(self, messages_panel):
        messages: [WhatsAppMessage] = []
        username = None

        def append_message(msg): messages.append(msg)
        self._for_each_message(messages_panel, append_message)

        for message in messages:
            # Split message content into words
            word_list = message.content.split()
            # Strip whitespace
            word_list = [word.strip() for word in word_list]

            # Find launch words
            launch_words = list(filter(lambda word: self.similar('launch', word.lower(), 0.7)
                                or self.similar('start', word.lower(), 0.7), word_list))

            if not launch_words or not message.content.strip().startswith(launch_words[0]):
                continue

            # Remove launch words
            word_list = [word for word in word_list if word not in launch_words]

            # Remaining words should be name and surname
            if not word_list:
                continue

            name, *surname = word_list
            username = " ".join(word_list)
            # Remove non-alpha characters
            username = "".join([c for c in username if c.isalpha() or c.isspace()])

            if username:
                return username

        return username

    def similar(self, a, b, threshold):
        return SequenceMatcher(None, a, b).ratio() >= threshold

    def _for_each_message(self, messages_panel, func):
        message_elements: [WebElement] = lambda: messages_panel \
            .find_elements_by_xpath(".//div[@class='vW7d1'][position() <= %d]" % MESSAGE_LIMIT)

        number_elements = len(message_elements())
        for index in range(number_elements):
            try:
                details_el: WebElement = message_elements()[index] \
                    .find_element_by_xpath(".//div[@class='Tkt2p']/div[1]")
            except NoSuchElementException:
                try:
                    details_el: WebElement = message_elements()[index] \
                        .find_element_by_xpath(".//div[@class='Tkt2p']/div[2]")
                except NoSuchElementException:
                    continue
            details = details_el.get_attribute('data-pre-plain-text')

            if details:
                time_string: str = details[details.find('[')+1:details.find(']')]
                sender_id: str = details.replace('[%s]' % time_string, '', 1).strip().replace(':', '', 1)
            else:
                continue

            # content: str = self.wait.until(lambda x: message_elements()[index].find_element_by_xpath(
            #     ".//span[@class='selectable-text invisible-space copyable-text']")).text
            try:
                content: str = message_elements()[index].find_element_by_xpath(
                    ".//span[@class='selectable-text invisible-space copyable-text']").text
            except NoSuchElementException:
                continue

            message = self.create_message('', time_string=time_string, sender_name=None,
                                          sender_number=sender_id, content=content)
            func(message)

    def create_message(self, uid, time_string, sender_name, sender_number, content):
        # Time string format: [18:44, 7/8/2018]
        # See http://strftime.org/
        # Timestamp can change, so using dateutil instead
        # timestamp = datetime.datetime.strptime(time_string, "%H:%M, %m/%d/%Y").replace(tzinfo=datetime.timezone.utc)

        timestamp = dateutil.parser.parse(time_string).replace(tzinfo=datetime.timezone.utc)
        msg = WhatsAppMessage(uid, timestamp, sender_name, sender_number, content)

        return msg

    def save_message(self, msg: WhatsAppMessage):
        # message_json = json.dumps(msg.__dict__, indent=4, sort_keys=True, default=str)
        # message_json = dumps(msg.__dict__)

        # Insert object into messages_collection and log database id
        try:
            schedule_id = self.messages_collection.insert_one(msg.__dict__).inserted_id
            print('Message inserted in database with ID ' + str(schedule_id))
            return schedule_id
        except WriteError:
            print('Duplicate message exists in database')
            return None

    def delete_message(self, msg_id):
        print('Deleting message from database')
        self.messages_collection.delete_many({"_id": msg_id})

    def purge_all_messages(self):
        print('Deleting all messages from database')
        self.messages_collection.delete_many({})

    def get_uid_from_number_db(self, contact_number):
        message = self.messages_collection.find_one({'sender_number': contact_number})
        if message:
            return message['uid']
        else:
            return None

    def messages_in_sync(self, last_message: WhatsAppMessage):
        last_message_dict = last_message.__dict__
        if self.messages_collection.find_one(last_message_dict):
            return True
        else:
            return False
