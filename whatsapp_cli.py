#!/usr/bin/env python3

import session_manager as session

import argparse
import time

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as exp_c
from selenium.webdriver.common.by import By
from selenium.common.exceptions import *

parser = argparse.ArgumentParser()

parser.add_argument('--message', help='send message', type=str, required=True)
parser.add_argument('--numbers', nargs='+', help='to numbers', required=True)

args = parser.parse_args()

TIMEOUT = 30

session = session.SessionManager()
driver = session.get_driver()
# session.save_cookies()

message = args.message
phone_numbers = args.numbers


def handle_alert():
    print("Processing alert")
    try:
        alert = driver.switch_to.alert
        alert.accept()
    except NoAlertPresentException as e:
        print(str(e))
        pass


def process_queue():
    print("Processing queue...")
    for number in phone_numbers:
        print('Ensuring connection okay')
        session.wait_until_connection_okay()

        print('Processing number ' + number)

        contact_header = None
        try:
            contact_header = driver.find_element_by_xpath("//header[@class='_3AwwN']")
        except NoSuchElementException:
            pass

        # If no contact open, load contact, else load next contact and wait for staleness of present contact
        if not contact_header:
            print('Contact header not present: fetching')
            driver.get('https://web.whatsapp.com/send?phone=' + number)
        else:
            print('Contact header present: refreshing')
            try:
                driver.get('https://web.whatsapp.com/send?phone=' + number)
                WebDriverWait(driver, TIMEOUT).until(
                    exp_c.staleness_of(contact_header)
                )
            except TimeoutException:
                session.restart_connection()
                continue
            finally:
                print('Page refreshed')

        try:
            content = WebDriverWait(driver, TIMEOUT).until(
                exp_c.visibility_of_element_located((By.XPATH, "//div[@contenteditable='true']"))
            )
            content.send_keys(message)
            print('Sending message to ' + number)
        except TimeoutException:
            session.restart_connection()
            continue
        finally:
            pass

        try:
            send_button = WebDriverWait(driver, TIMEOUT).until(
                exp_c.visibility_of_element_located((By.CLASS_NAME, "_2lkdt"))
            )
            send_button.click()
            print('Message sent to ' + number)
        except TimeoutException:
            session.restart_connection()
            continue
        finally:
            pass

        try:
            attach = WebDriverWait(driver, TIMEOUT).until(
                exp_c.visibility_of_element_located((By.XPATH, "//div[@title='Attach']"))
            )
            attach.click()
            print('Attaching file for ' + number)
        except TimeoutException:
            session.restart_connection()
            continue
        finally:
            pass

        try:
            file = driver.find_element_by_xpath("//input[@accept='*']")
            driver.execute_script("arguments[0].style.display='block';", file)
            WebDriverWait(driver, TIMEOUT).until(
                exp_c.visibility_of(file)
            )
            file.send_keys("/home/bscholtz/Music/Scottish_Motivation_2_Promise_Yourself.mp3")
            print('File attached for ' + number)
        except TimeoutException:
            session.restart_connection()
            continue
        finally:
            pass

        try:
            print('Sending attachment to ' + number)
            send_file = WebDriverWait(driver, TIMEOUT).until(
                exp_c.visibility_of_element_located((By.XPATH, "//div[@class='_3hV1n yavlE']"))
            )
            send_file.click()
            print('Waiting for attachment to upload')
            WebDriverWait(driver, TIMEOUT).until(
                exp_c.visibility_of_element_located((By.XPATH, "//div[@class='_3SUnz']"))
            )
            WebDriverWait(driver, TIMEOUT).until(
                exp_c.invisibility_of_element_located((By.XPATH, "//div[@class='_3SUnz']"))
            )
            print('Attachment sent to ' + number)
        except TimeoutException:
            session.restart_connection()
            continue
        finally:
            pass


try:
    process_queue()
except UnexpectedAlertPresentException as e:
    print("UnexpectedAlertPresentException: " + str(e))
    handle_alert()
