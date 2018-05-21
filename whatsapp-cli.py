#!/usr/bin/env python3

import argparse
import time, sys
from selenium import webdriver
from selenium.webdriver.firefox.firefox_binary import FirefoxBinary
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as exp_c
from selenium.webdriver.common.by import By
from selenium.common.exceptions import *

TIMEOUT = 30

parser = argparse.ArgumentParser()

parser.add_argument('--message', help='send message', type=str, required=True)
parser.add_argument('--numbers', nargs='+', help='to numbers', required=True)

args = parser.parse_args()

print('Fetching Firefox binary...')
binary = FirefoxBinary('/usr/bin/firefox-developer-edition')
webdriver.DesiredCapabilities.FIREFOX["unexpectedAlertBehaviour"] = "accept"
web = webdriver.Firefox(firefox_binary=binary)
web.implicitly_wait(TIMEOUT)

message = args.message
phone_numbers = args.numbers

print('Loading WhatsApp web - scan barcode when prompted')
# input("Press Enter to continue...")
web.get('https://web.whatsapp.com/send?phone=' + phone_numbers[0])

print('Waiting for page to load...')

try:
    element = WebDriverWait(web, TIMEOUT).until(
        exp_c.presence_of_element_located((By.XPATH, "//div[@contenteditable='true']"))
    )
except TimeoutException:
    print('Error: waited too long for barcode scan')
    exit(0)

print('Page load finished')


def handle_alert():
    try:
        alert = web.switch_to.alert
        alert.accept()
    except NoAlertPresentException:
        return


for number in phone_numbers:
    print('Fetching contact ' + number)
    content = web.find_element_by_xpath("//div[@contenteditable='true']")

    try:
        web.get('https://web.whatsapp.com/send?phone=' + number)
        handle_alert()
        element = WebDriverWait(web, TIMEOUT).until(
            exp_c.staleness_of(content)
        )
    finally:
        print('Page refreshed')

    try:
        attach = WebDriverWait(web, TIMEOUT).until(
            exp_c.presence_of_element_located((By.XPATH, "//div[@title='Attach']"))
        )
    except TimeoutException:
        exit(0)
    finally:
        attach.click()
        print('Attaching file for ' + number)

    try:
        file = web.find_element_by_xpath("//input[@accept='*']")
        web.execute_script("arguments[0].style.display='block';", file)
        WebDriverWait(web, TIMEOUT).until(
            exp_c.visibility_of(file)
        )
    except TimeoutException:
        exit(0)
    finally:
        print('File attached for ' + number)
        file.send_keys("/home/bscholtz/Music/Scottish_Motivation_2_Promise_Yourself.mp3")

    try:
        print('Sending attachment to ' + number)
        sendFile = WebDriverWait(web, TIMEOUT).until(
            exp_c.presence_of_element_located((By.XPATH, "//div[@class='_3hV1n yavlE']"))
        )
    except TimeoutException:
        exit(0)
    finally:
        print('Attachment sent to ' + number)
        sendFile.click()

    try:
        content = WebDriverWait(web, TIMEOUT).until(
            exp_c.presence_of_element_located((By.XPATH, "//div[@contenteditable='true']"))
        )
    except TimeoutException:
        exit(0)
    finally:
        print('Sending message to ' + number)
        content.send_keys(message)

    try:
        send_button = WebDriverWait(web, TIMEOUT).until(
            exp_c.presence_of_element_located((By.CLASS_NAME, "_2lkdt"))
        )
    except TimeoutException:
        exit(0)
    finally:
        print('Message sent to ' + number)
        send_button.click()
