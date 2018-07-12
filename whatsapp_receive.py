#!/usr/bin/env python3

from bson.json_util import dumps
import json
import time
import datetime
from collections import deque

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

from session_manager import SessionManager
from message import Message

TIMEOUT = 30

binary = FirefoxBinary('/usr/bin/firefox-developer-edition')
webdriver.DesiredCapabilities.FIREFOX["unexpectedAlertBehaviour"] = "accept"


class WhatsAppReceive:

    def __init__(self) -> None:
        super().__init__()

        # self.session = SessionManager
        # self.driver = self.session.get_existing_driver_session()

        self._initialize_database()

        self.driver = webdriver.Firefox(firefox_binary=binary)
        self.driver.get('https://web.whatsapp.com/')

    def _initialize_database(self):
        self.client = MongoClient('localhost', 27017)
        self.db = self.client.whatsapp_cli

        # MongoDB scales horizontally, so: single messages collection containing all messages from all conversations
        #
        self.messages_collection: Collection = self.db.messages
        # self.messages_collection.create_index([("uid", pymongo.DESCENDING)], unique=True)

    def process_conversations(self):
        print('Ensuring connection okay')
        # self.session.wait_until_connection_okay()

        print('Fetching conversations panel')
        conversations_panel: WebElement = self._get_conversations_panel()
        print('Fetching conversations')
        conversations: [WebElement] = conversations_panel.find_elements_by_class_name('_2wP_Y')

        previous_conversation_content = None

        print('Processing conversations')
        for conversation in conversations:
            name = conversation.find_element_by_xpath("//span[@class='_1wjpf']").get_attribute('title')
            last_message = conversation.find_element_by_xpath("//span[@class='_2_LEW']").get_attribute('title')
            print('Processing conversation: Name - %s ~ Last Message - %s' % (name, last_message))

            # If moving from active conversation, wait for content to refresh after click
            conversation.click()
            if previous_conversation_content:
                WebDriverWait(self.driver, TIMEOUT).until(
                    exp_c.staleness_of(previous_conversation_content)
                )

            messages_panel = WebDriverWait(self.driver, TIMEOUT).until(
                exp_c.visibility_of_element_located((By.XPATH, "//div[@class='_9tCEa']"))
            )
            previous_conversation_content = messages_panel
            messages = self._extract_conversation_messages(messages_panel)

            for message in messages:
                print('Saving message to database')
                self.save_message(message)

    def _get_conversations_panel(self):
        conversations_panel = None
        try:
            conversations_panel = WebDriverWait(self.driver, TIMEOUT).until(
                exp_c.visibility_of_element_located((By.XPATH, "//div[@class='RLfQR']"))
            )
        except TimeoutException:
            pass
        return conversations_panel

    def _extract_conversation_messages(self, messages_panel):
        message_elements: [WebElement] = messages_panel.find_elements_by_class_name('vW7d1')
        messages: [Message] = []

        for msg in message_elements:
            try:
                details_el: WebElement = msg.find_element_by_xpath("//div[@class='Tkt2p']/div[1]")
            except NoSuchElementException:
                try:
                    details_el: WebElement = msg.find_element_by_xpath("//div[@class='Tkt2p']/div[2]")
                except NoSuchElementException:
                    print('No details')
                    continue
            details = details_el.get_attribute('data-pre-plain-text')

            if details:
                print('Details: %s' % details)
                time_string: str = "[%s]" % details[details.find('[')+1:details.find(']')]
                sender_name: str = details.replace(time_string, '', 1).strip().replace(':', '', 1)
            else:
                print('No details')
                continue

            content: str = msg.find_element_by_xpath("//span[@class='selectable-text invisible-space copyable-text']").text

            message = self.create_message(sender_name, time_string, sender_name, content)
            print('Message: %s' % message)
            messages.append(message)

        return messages

    def create_message(self, uid, time_string, sender_name, content):
        # Time string format: [18:44, 7/8/2018]
        # See http://strftime.org/
        timestamp = datetime.datetime.strptime(time_string, "[%H:%M, %m/%d/%Y]").replace(tzinfo=datetime.timezone.utc)

        msg = Message(uid, timestamp, sender_name, content)
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


if __name__ == '__main__':
    print('Procesing WhatsApp conversations')
    whatsapp_receive = WhatsAppReceive()
    whatsapp_receive.process_conversations()
