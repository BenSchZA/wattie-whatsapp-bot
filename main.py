#!/usr/bin/env python3

from selenium import webdriver

driver = webdriver.Remote(command_executor='http://localhost:4444/wd/hub',
                          desired_capabilities=webdriver.DesiredCapabilities.FIREFOX)
