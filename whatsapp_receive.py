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

import pymongo
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.errors import WriteError

# from session_manager import SessionManager
from message import Message
import re
import requests
import os
import whatsapp_cli_interface

TIMEOUT = 30
MESSAGE_LIMIT = 5

binary = FirefoxBinary('/usr/bin/firefox-developer-edition')
webdriver.DesiredCapabilities.FIREFOX["unexpectedAlertBehaviour"] = "accept"


class WhatsAppReceive:

    def __init__(self) -> None:
        super().__init__()

        self._initialize_database()

        # self.session = SessionManager
        # self.driver = self.session.get_existing_driver_session()

        self.driver = webdriver.Firefox(firefox_binary=binary)
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

    def process_contacts(self):
        # self._for_each_conversation(self._process_contact)
        # print(self.processed_contacts)
        self.processed_contacts = ['+27 61 025 7217', '+27 83 790 2536', '+27 74 475 9415', '+27 82 569 6732', '+27 83 234 6500', '+27 72 552 9500', '+27 72 086 3377', '+27 78 147 4533', '+27 79 690 0576', '+27 72 452 6334', '+27 73 598 7254', '+27 71 851 6687', '+27 83 569 1785', '+27 63 887 7920', '+27 76 299 7577', '+27 72 117 4999', '+27 84 847 7666', '+27 82 454 4293', '+27 82 574 7645', '+27 76 488 8118', '+27 63 245 9335', '+27 76 765 3373', '+27 82 505 0944', '+27 72 878 0777', '+27 66 268 4344', '+27 83 225 5305', '+27 82 782 4655', '+27 76 555 9180', '+254 729 406636', '+27 83 586 3979', '+27 84 903 4239', '+27 79 174 0483', '+27 72 117 4645', '+27 84 988 8009', '+27 83 782 1847', '+27 72 170 6082', '+27 76 339 2072', '+27 82 520 2118', '+27 82 718 4043', '+27 71 403 9117', '+27 72 268 5444', '+27 72 271 5617', '+27 79 883 6590', '+44 7747 455486', '+27 72 879 6256', '+27 82 083 1791', '+27 82 789 5023', '+27 82 726 5477', '+27 72 868 0428', '+27 83 644 6256', '+27 60 526 3989', '+27 83 641 9768', '+27 78 185 4892', '+27 83 610 1720', '+27 83 695 0440', '+27 83 890 9997', '+27 82 616 1888', '+27 72 686 3630', '+27 79 888 2983', '+27 83 563 8250', '+230 5939 9446', '+27 73 281 4936', '+27 76 473 8036', '+27 84 548 4828', '+27 72 594 3791', '+27 82 372 9509', '+27 83 208 8177', '+27 61 529 5517', '+27 74 291 5624', '+27 83 655 5885', '+27 83 649 8122', '+27 72 802 3733', '+27 82 447 8625', '+27 82 681 0831', '+27 72 309 6454', '+27 82 654 5090', '+27 72 171 7502', '+27 82 444 3668', '+27 83 302 6562', '+27 73 312 3180', '+27 76 546 6362', '+31 6 25542303', '+27 72 603 6565', '+44 7802 591562', '+27 76 903 8900', '+27 76 841 2166', '+27 72 255 2972', '+27 79 060 7985', '+27 84 907 0206', '+27 71 261 2777', '+27 72 285 1202', '+27 72 100 7365', '+27 82 465 9237', '+27 84 011 2999', '+27 72 317 5604', '+27 71 252 2440', '+27 72 606 0849', '+27 78 431 6035', '+27 76 981 8868', '+27 83 529 3383', '+27 73 993 2253', '+44 7557 564426', '+27 82 557 1745', '+27 83 772 3555', '+27 78 458 0456', '+27 72 566 5265', '+27 83 642 9919', '+27 74 724 2213', '+27 72 252 9709', '+27 82 092 6188', '+27 82 997 0202', '+44 7961 298559', '+27 82 784 7595', '+27 82 517 2909', '+27 82 422 5011', '+27 84 251 2548', '+27 82 573 4346', '+44 7733 764044', '+27 72 041 2224', '+27 79 468 5667', '+27 82 908 7087', '+27 76 352 7676', '+27 84 207 0633', '+27 84 509 3478', '+27 83 229 4250', '+27 71 415 9432', '+27 72 614 4349', '+27 74 101 2090', '+27 76 453 0288', '+27 71 203 1966', '+27 76 958 2839', '+27 72 427 9757', '+27 82 962 5919', '+27 72 060 2662', '+27 61 636 8556', '+27 82 307 7715', '+27 84 883 9243', '+27 72 342 7111', '+27 81 491 9950', '+27 82 455 5505', '+44 7428 160051', '+27 79 962 1040', '+27 82 554 3719', '+27 72 658 9311', '+27 72 474 5096', '+27 83 227 8808', '+27 76 927 5539', '+27 79 772 5078', '+44 7341 939936', '+27 82 922 9046', '+27 82 943 1891', '+27 76 215 8482', '+27 76 908 7688', '+27 76 551 1667', '+27 83 796 7018', '+27 79 497 7634', '+31 6 21252107', '+27 83 474 5988', '+27 79 773 1066', '+27 82 417 6708', '+27 82 457 1522', '+27 82 781 7731', '+44 7785 984265', '+27 72 471 0676', '+27 76 221 5822', '+27 83 298 9554', '+27 79 455 0434', '+27 78 265 8128', '+27 84 696 9161', '+27 82 442 6133', '+27 82 882 7897', '+27 71 347 4089', '+27 83 448 4883', '+27 71 205 3988', '+27 79 344 0064', '+27 72 037 6032', '+44 7584 557571', '+27 74 619 9334', '+27 83 275 8628', '+44 7917 481242', '+264 81 347 7018', '+27 72 774 6577', '+27 79 672 0317', '+27 63 688 9878', '+27 72 197 2014', '+27 82 399 7763', '+27 82 730 8426', '+49 1525 4686401', '+27 72 250 8057', '+27 78 193 2253', '+27 61 342 8004', '+27 72 200 3152', '+27 82 500 7575', '+27 60 570 8688', '+27 74 105 7634', '+27 73 191 5974', '+27 79 926 3236', '+27 76 765 4990', '+27 84 548 2588', '+31 6 39246886', '+27 83 648 7115', '+27 66 223 5708', '+27 83 793 1293', '+27 76 536 4955', '+44 7510 033159', '+27 76 546 9207', '+27 79 798 8558', '+27 82 671 6389', '+27 84 451 1077', '+27 83 271 1500', '+27 72 745 1130', '+27 73 102 0363', '+27 82 602 0629', '+27 82 969 7286', '+27 76 867 1859', '+49 1520 4696098', '+27 76 461 1826', '+27 81 430 3822', '+263 71 334 1032', '+27 82 887 4759', '+27 82 446 4421', '+27 83 630 2779', '+27 81 327 5680', '+27 82 585 6424', '+27 84 413 4627', '+27 82 929 7015', '+27 72 222 2006', '+27 71 898 2677', '+27 82 530 1161', '+27 82 566 3708', '+27 82 974 1847', '+27 79 492 1808', '+27 82 451 6848', '+27 79 075 2000', '+27 61 448 3168', '+27 83 669 4011', '+27 82 387 4046', '+27 82 417 7501', '+27 76 381 1235', '+27 82 335 9000', '+31 6 22845631', '+27 71 755 1881', '+27 81 560 1784', '+27 82 925 3598', '+44 7522 759951', '+27 72 405 4400', '+44 7717 069698', '+230 5941 6327', '+44 7490 599562', '+27 78 120 2558', '+27 78 186 3014', '+27 83 402 5563', '+27 76 338 1243', '+27 84 957 0353']

        # print(len(self.processed_contacts))
        # new_user_contacts = ['+27 84 957 0353']
        # Michelle Becker failed
        # Wattie: '+27 84 957 0353'
        # print(len(new_user_contacts))
        # new_user_contacts = self._get_new_user_contacts()
        # print(new_user_contacts)
        new_user_contacts = ['+27 61 025 7217', '+27 83 790 2536', '+27 74 475 9415', '+27 82 569 6732', '+27 83 234 6500', '+27 72 552 9500', '+27 72 086 3377', '+27 78 147 4533', '+27 79 690 0576', '+27 72 452 6334', '+27 73 598 7254', '+27 71 851 6687', '+27 83 569 1785', '+27 63 887 7920', '+27 76 299 7577', '+27 72 117 4999', '+27 84 847 7666', '+27 82 454 4293', '+27 82 574 7645', '+27 76 488 8118', '+27 63 245 9335', '+27 76 765 3373', '+27 82 505 0944', '+27 72 878 0777', '+27 66 268 4344', '+27 83 225 5305', '+27 82 782 4655', '+27 76 555 9180', '+254 729 406636', '+27 83 586 3979', '+27 84 903 4239', '+27 79 174 0483', '+27 72 117 4645', '+27 84 988 8009', '+27 83 782 1847', '+27 72 170 6082', '+27 76 339 2072', '+27 82 520 2118', '+27 82 718 4043', '+27 71 403 9117', '+27 72 268 5444', '+27 72 271 5617', '+27 79 883 6590', '+44 7747 455486', '+27 72 879 6256', '+27 82 083 1791', '+27 82 789 5023', '+27 82 726 5477', '+27 72 868 0428', '+27 83 644 6256', '+27 60 526 3989', '+27 83 641 9768', '+27 78 185 4892', '+27 83 610 1720', '+27 83 695 0440', '+27 82 616 1888', '+27 83 563 8250', '+230 5939 9446', '+27 73 281 4936', '+27 76 473 8036', '+27 84 548 4828', '+27 84 957 0353']

        print('Checking for new users')
        while True:
            if not new_user_contacts:
                break
            for number in new_user_contacts:
                conversation = self._find_conversation_by_id(number)
                if conversation:
                    self._process_conversation(conversation)
                    new_user_contacts.remove(number)
            scroll_progress = self._side_pane_scroll_top()
            scroll_max = self._side_pane_scroll_top_max()
            if scroll_progress == scroll_max:
                self._side_pane_scroll_to(0)
            else:
                self._side_pane_scroll_by(500)

        # self.processed_contacts = list(map(lambda contact: self._clean_contact_number(contact), self.processed_contacts))
        # self.processed_contacts = list(filter(None.__ne__, self.processed_contacts))
        #
        # for number in self.processed_contacts:
        #     print('Number: %s _ %s' % (number, self._get_uid_from_number(number)))
        # print(self.processed_contacts)

    def send_welcome_message(self, contact_id):
        message = "Welcome to ***REMOVED*** my bok boks"
                  # "\n\nWe’re still in the testing phase " \
                  # "(we even have to use Dom & Josh’s voices for now, bless them)," \
                  # " so if you have any feedback or need help message this ***REMOVED*** number %s" \
                  # "\n\nEach Thursday morning we send out your ***REMOVED***, via a mp3 file and a link. " \
                  # "The link let’s you listen on our web app where you can customise your ***REMOVED*** %s" \
                  # "\n\nThanks for being curious my special person!" \
                  # % ('test1', 'test2')

        # '\U0001F44D'.encode('unicode_escape'), '\U0001F60E'.encode('unicode-escape')

        params = {
            'number': contact_id,
            'message': message,
        }

        headers = {
            'X-Auth-Token': os.environ['AUTH_TOKEN']
        }

        req = requests.get("http://localhost:8001/message", params=params, headers=headers)

        if req.status_code == 200:
            print('Message delivered to %s' % contact_id)
            print('%s %s' % (req.status_code, req.reason))
            return True
        else:
            print('Message failed to deliver to %s' % contact_id)
            print('%s %s' % (req.status_code, req.reason))
            return False

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

            last_message = Message(uid=uid, timestamp=None, sender_name=None, sender_number=contact_id, content=last_message_content)
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
            messages = self._extract_and_save_messages(messages_panel)
            print('Saving messages to database')
            for message in messages:
                message.uid = uid
                self.save_message(message)
                print('Message: %s' % message.__dict__)
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

    def _extract_and_save_messages(self, messages_panel):
        messages: [Message] = []

        def append_message(message): messages.append(message)
        self._for_each_message(messages_panel, append_message)

        return messages

    def _process_new_user(self, messages_panel):
        messages: [Message] = []
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
        msg = Message(uid, timestamp, sender_name, sender_number, content)

        return msg

    def save_message(self, msg: Message):
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

    def messages_in_sync(self, last_message: Message):
        last_message_dict = last_message.__dict__
        if self.messages_collection.find_one(last_message_dict):
            return True
        else:
            return False


def debug():
    print('Procesing WhatsApp conversations')
    whatsapp_receive = WhatsAppReceive()
    # print(whatsapp_receive._get_uid_from_number('+27763381243'))
    # whatsapp_receive.process_contacts()
    # whatsapp_receive.process_messages()

    # new_user_contacts = ['+27 61 025 7217', '+27 83 790 2536', '+27 74 475 9415', '+27 82 569 6732', '+27 83 234 6500', '+27 72 552 9500', '+27 72 086 3377', '+27 78 147 4533', '+27 79 690 0576', '+27 72 452 6334', '+27 73 598 7254', '+27 71 851 6687', '+27 83 569 1785', '+27 63 887 7920', '+27 76 299 7577', '+27 72 117 4999', '+27 84 847 7666', '+27 82 454 4293', '+27 82 574 7645', '+27 76 488 8118', '+27 63 245 9335', '+27 76 765 3373', '+27 82 505 0944', '+27 72 878 0777', '+27 66 268 4344', '+27 83 225 5305', '+27 82 782 4655', '+27 76 555 9180', '+254 729 406636', '+27 83 586 3979', '+27 84 903 4239', '+27 79 174 0483', '+27 72 117 4645', '+27 84 988 8009', '+27 83 782 1847', '+27 72 170 6082', '+27 76 339 2072', '+27 82 520 2118', '+27 82 718 4043', '+27 71 403 9117', '+27 72 268 5444', '+27 72 271 5617', '+27 79 883 6590', '+44 7747 455486', '+27 72 879 6256', '+27 82 083 1791', '+27 82 789 5023', '+27 82 726 5477', '+27 72 868 0428', '+27 83 644 6256', '+27 60 526 3989', '+27 83 641 9768', '+27 78 185 4892', '+27 83 610 1720', '+27 83 695 0440', '+27 82 616 1888', '+27 83 563 8250', '+230 5939 9446', '+27 73 281 4936', '+27 76 473 8036', '+27 84 548 4828', '+27 84 957 0353']
    #
    # for contact in new_user_contacts:
    #     whatsapp_receive.send_welcome_message(contact)

    whatsapp_receive.send_welcome_message('+27 76 338 1243')


if __name__ == '__main__':
    print('Procesing WhatsApp conversations')
    whatsapp_receive = WhatsAppReceive()
    # print(whatsapp_receive._get_uid_from_number('+27763381243'))
    # whatsapp_receive.process_contacts()
    # whatsapp_receive.process_messages()

    # new_user_contacts = ['+27 61 025 7217', '+27 83 790 2536', '+27 74 475 9415', '+27 82 569 6732', '+27 83 234 6500', '+27 72 552 9500', '+27 72 086 3377', '+27 78 147 4533', '+27 79 690 0576', '+27 72 452 6334', '+27 73 598 7254', '+27 71 851 6687', '+27 83 569 1785', '+27 63 887 7920', '+27 76 299 7577', '+27 72 117 4999', '+27 84 847 7666', '+27 82 454 4293', '+27 82 574 7645', '+27 76 488 8118', '+27 63 245 9335', '+27 76 765 3373', '+27 82 505 0944', '+27 72 878 0777', '+27 66 268 4344', '+27 83 225 5305', '+27 82 782 4655', '+27 76 555 9180', '+254 729 406636', '+27 83 586 3979', '+27 84 903 4239', '+27 79 174 0483', '+27 72 117 4645', '+27 84 988 8009', '+27 83 782 1847', '+27 72 170 6082', '+27 76 339 2072', '+27 82 520 2118', '+27 82 718 4043', '+27 71 403 9117', '+27 72 268 5444', '+27 72 271 5617', '+27 79 883 6590', '+44 7747 455486', '+27 72 879 6256', '+27 82 083 1791', '+27 82 789 5023', '+27 82 726 5477', '+27 72 868 0428', '+27 83 644 6256', '+27 60 526 3989', '+27 83 641 9768', '+27 78 185 4892', '+27 83 610 1720', '+27 83 695 0440', '+27 82 616 1888', '+27 83 563 8250', '+230 5939 9446', '+27 73 281 4936', '+27 76 473 8036', '+27 84 548 4828', '+27 84 957 0353']
    #
    # for contact in new_user_contacts:
    #     whatsapp_receive.send_welcome_message(contact)

    whatsapp_receive.send_welcome_message('27763381243')
