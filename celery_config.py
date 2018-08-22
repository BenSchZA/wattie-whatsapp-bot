from kombu import Queue
from celery import Celery

import datetime
from enum import Enum


class Queues(Enum):
    download = 1
    deliver = 2
    send_message = 3
    process_message = 4


app = Celery('tasks', broker='redis://redis')

app.conf.task_queues = (
    Queue(Queues.download.name, queue_arguments={'x-max-priority': 8}),
    Queue(Queues.deliver.name, queue_arguments={'x-max-priority': 10}),
    Queue(Queues.send_message.name, queue_arguments={'x-max-priority': 9}),
    Queue(Queues.process_message.name, queue_arguments={'x-max-priority': 1})
)
app.conf.task_queue_max_priority = 10

app.conf.timezone = 'UTC'
app.conf.beat_schedule = {
    'process-new-users_every-3-hours': {
        'task': 'tasks.process_new_users',
        'schedule': datetime.timedelta(hours=3),
        'relative': True,
        'options': {'queue': 'process_message', 'task_id': 'unique_process-new-users'}
    }
}
