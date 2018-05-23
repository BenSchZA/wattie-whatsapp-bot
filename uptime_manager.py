import time
import csv


def process_up(context):
    with open('uptime.csv', 'a+') as outfile:
        outfile.write(_get_csv_string(context) + ',' + 'up\n')


def process_down(context):
    with open('uptime.csv', 'a+') as outfile:
        outfile.write(_get_csv_string(context) + ',' + 'down\n')


def _get_csv_string(context):
    return str(int(round(time.time() * 1000))) + ',' + str(time.ctime()) + ',' + context.__class__.__name__


def get_uptime(context):
    uptime = 0
    last_millis = 0
    with open('uptime.csv', 'r+') as csv_file:
        read_csv = csv.reader(csv_file, delimiter=',')
        for row in read_csv:
            millis = int(row[0])
            class_name = row[2]
            status = row[3]
            if class_name == context.__class__.__name__:
                if status == 'up':
                    interval = millis - last_millis
                    if last_millis == 0:
                        interval = 10000
                    uptime += interval
                    last_millis = millis
                else:
                    last_millis = 0
    return uptime


def get_downtime(context):
    downtime = 0
    last_millis = 0
    with open('uptime.csv', 'r+') as csv_file:
        read_csv = csv.reader(csv_file, delimiter=',')
        for row in read_csv:
            millis = int(row[0])
            class_name = row[2]
            status = row[3]
            if class_name == context.__class__.__name__:
                if status == 'down':
                    interval = millis - last_millis
                    if last_millis == 0:
                        interval = 10000
                    downtime += interval
                    last_millis = millis
                else:
                    last_millis = 0
    return downtime


def get_uptime_percent(context):
    uptime = get_uptime(context)
    downtime = get_downtime(context)

    return (uptime*100)/(uptime + downtime)
