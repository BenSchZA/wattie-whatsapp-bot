from selenium.common.exceptions import *
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as exp_c
from selenium.webdriver.common.by import By

TIMEOUT = 30


def _clear_search(driver):
    try:
        clear_search = driver.find_element_by_xpath("//button[@class='_3Burg']")
        clear_search.click()
    except (NoSuchElementException, StaleElementReferenceException, ElementClickInterceptedException):
        pass


def is_valid_numeric(string):
    for char in string:
        if char.isdigit() or char == '+':
            continue
        else:
            return False
    return True


def clean_contact_number(contact_number):
    if not contact_number:
        return None
    contact_number = contact_number.replace(' ', '').replace('(', '').replace(')', '').replace('-', '')
    if is_valid_numeric(contact_number):
        return contact_number
    else:
        return None


def try_search_for_contact(driver, contact_number):
    # Enter search text
    try:
        search_bar = WebDriverWait(driver, TIMEOUT).until(
            exp_c.visibility_of_element_located((By.XPATH, "//input[@class='jN-F5 copyable-text selectable-text']"))
        )
        search_bar.click()
        search_bar.send_keys(contact_number)
        print('Searching for contact ' + contact_number)
    except (ElementClickInterceptedException, TimeoutException):
        return False
    # If no contacts found, return False
    try:
        driver.find_element_by_xpath("//div[@class='_3WZoe']")
        print('No contacts found')
        _clear_search(driver)
        return False
    except NoSuchElementException:
        print('Contact found')
        pass
    # Else Press enter
    try:
        if search_bar:
            print('Selecting contact conversation')
            search_bar.send_keys(Keys.RETURN)
            _clear_search(driver)
    except ElementClickInterceptedException:
        _clear_search(driver)
        return False
    # Check contact header for correct number
    try:
        print('Waiting for contact header')
        contact_header = WebDriverWait(driver, 5).until(lambda _: driver.find_element_by_xpath("//header[@class='_3AwwN']"))
    except TimeoutException:
        return False
    try:
        print('Fetching contact ID')
        contact_id = WebDriverWait(driver, TIMEOUT).until(lambda _: contact_header.find_element_by_xpath(".//span[@class='_1wjpf']")) \
            .get_attribute('title')
    except TimeoutException:
        return False

    contact_id = clean_contact_number(contact_id)
    contact_number = clean_contact_number(contact_number)

    print('Contact ID %s ~ Contact number %s' % (contact_id, contact_number))
    if contact_id and contact_number:
        contact_id = contact_id.replace("+", "")
        contact_number = contact_number.replace("+", "")
        return contact_id == contact_number
    else:
        return False
