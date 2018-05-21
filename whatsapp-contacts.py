#!/usr/bin/env python3

import argparse
import time, sys
from selenium import webdriver
from selenium.webdriver.firefox.firefox_binary import FirefoxBinary
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as exp_c
from selenium.webdriver.common.by import By
from selenium.common.exceptions import *
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

TIMEOUT = 30

parser = argparse.ArgumentParser()

parser.add_argument('-message', help='send message', type=str, required=True)
parser.add_argument('-numbers', nargs='+', help='to numbers', required=True)

args = parser.parse_args()

print('Fetching Firefox binary...')
binary = FirefoxBinary('/usr/bin/firefox-developer-edition')
webdriver.DesiredCapabilities.FIREFOX["unexpectedAlertBehaviour"] = "accept"
web = webdriver.Firefox(firefox_binary=binary)
web.implicitly_wait(1)

actions = ActionChains(web)

message = args.message
phone_numbers = args.numbers

print('Loading WhatsApp web - scan barcode when prompted')
web.get('https://web.whatsapp.com/')

print('Waiting for page to load...')
try:
    element = WebDriverWait(web, TIMEOUT).until(
        exp_c.presence_of_element_located((By.CLASS_NAME, "_3qlW9"))
    )
except TimeoutException:
    print('Error: waited too long for barcode scan')
    exit(0)

print('Page load finished')

contacts = []


class Contact:
    numbers = []

    def __init__(self, name, chat_element):
        self.name = name
        self.chat_element = chat_element

    def append_number(self, __number):
        self.numbers.append(__number)


def handle_alert():
    try:
        alert = web.switch_to.alert
        alert.accept()
    except NoAlertPresentException:
        return


def get_all_contacts():
    chat_button = web.find_element_by_xpath("//div[@title='New chat']")
    WebDriverWait(web, TIMEOUT).until(exp_c.visibility_of(chat_button))
    chat_button.click()

    side_pane = web.find_element_by_class_name("_2sNbV")

    chat_element = side_pane.find_element_by_class_name("_2EXPL")
    actions.move_to_element(chat_element).perform()

    while True:
        if chat_element.text != 'New group':

            print("Processing contact element " + chat_element.text)
            chat_element.click()

            # chat_button = web.find_element_by_xpath("//div[@title='New chat']")
            # WebDriverWait(web, 1).until(exp_c.visibility_of(chat_button))
            # chat_button.click()

            try:
                contact_info__button = web.find_element_by_xpath("//div[@title='Contact info']")
                contact_info__button.click()
            except NoSuchElementException:
                # Chat is a group chat
                continue
            finally:
                try:
                    chat_element = chat_element.find_element_by_xpath("/following-sibling::div/")
                    actions.move_to_element(chat_element).perform()
                except NoSuchElementException:
                    print("No element")

            contact_name = web.find_element_by_class_name("iYPsH")
            contact_numbers = web.find_elements_by_class_name("_3LL06")

            contact = Contact(contact_name.text, chat_element)
            for contact_number in contact_numbers:
                contact.append_number(contact_number.text)
            contacts.append(contact)

        try:
            chat_element = chat_element.find_element_by_xpath("/following-sibling::div/")
            actions.move_to_element(chat_element).perform()
        except NoSuchElementException:
            continue


def select_contact(__number):
    contact = None
    try:
        contact = next(filter(lambda x: __number in x.numbers, contacts), None)
    except StopIteration:
        print("No such contact")

    if contact:
        return contact.chat_element.click()
    else:
        return False


def send_message(__number, __message):
    __content = None
    send_button = None

    try:
        __content = WebDriverWait(web, TIMEOUT).until(
            exp_c.presence_of_element_located((By.XPATH, "//div[@contenteditable='true']"))
        )
    except TimeoutException:
        exit(0)
    finally:
        print('Sending message to ' + __number)
        __content.send_keys(__message)

    try:
        send_button = WebDriverWait(web, TIMEOUT).until(
            exp_c.presence_of_element_located((By.CLASS_NAME, "_2lkdt"))
        )
    except TimeoutException:
        exit(0)
    finally:
        send_button.click()


send_message(27763381243, 'Hello')


get_all_contacts()

for number in phone_numbers:
    print('Fetching contact ' + number)

    content = web.find_element_by_xpath("//div[@contenteditable='true']")

    if select_contact(number):
        send_message(number, message)

    else:
        try:
            web.get('https://web.whatsapp.com/send?phone=' + number)
            handle_alert()
            element = WebDriverWait(web, TIMEOUT).until(
                exp_c.staleness_of(content)
            )
        except TimeoutException:
            exit(0)
        finally:
            print('Page refreshed')

        send_message(number, message)
