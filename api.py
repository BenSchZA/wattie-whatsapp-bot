from flask import Flask, request
from flask_restful import Resource, Api
from whatsapp_cli_interface import send_whatsapp

app = Flask(__name__)
api = Api(app)


@app.route("/health")
def health_check():
    return 'healthy'


@app.route('/message')
def send_whatsapp_message():
    number = request.args.get('number')
    message = request.args.get('message')

    send_whatsapp(number=number, message=message)

    return 'Sending message %s to %s' % (message, number)


def start():
    app.run(port='8001')


if __name__ == '__main__':
    app.run(port='8001')
