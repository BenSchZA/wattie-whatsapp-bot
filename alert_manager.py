# ***REMOVED***
import requests
import os


class AlertManager:

    def __init__(self) -> None:
        super().__init__()

    @staticmethod
    def slack_alert(text):
        slack_data = {'text': text}
        return requests.post(os.environ['SLACK_HOOK_URL'], json=slack_data, headers={'Content-Type': 'application/json'})
