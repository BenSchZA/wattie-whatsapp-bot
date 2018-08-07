# Wattie WhatsApp bot - selenium-whatsapp

---

# Components

---

## SessionManager Class

Class for managing active Selenium session via Selenium Hub & Selenium Node:

* Restarting/refreshing driver session
* Persisting last session for reloading
* Monitoring uptime and restarting services when necessary

### UptimeManager Class

Class used for logging session uptime during operation.

## ScheduleManager Class

Class for handling scheduled ***REMOVED*** deliveries and pushing to Celery task queues.

## API Module

The API provides the following functionality:

1. Checking service health
2. Manually starting schedule handling
3. Sending WhatsApp messages

All transaction are routed through the API. The benefit of routing all transactions via the API is that we can use ElasticAPM to provide performance metrics e.g. the time it takes to deliver a ***REMOVED***.

## FileManager Class

The FileManager handles the following tasks:

1. Downloading files to be delivered
2. Purging downloaded files when appropriate
3. Tracking all files downloaded by creating a MongoDB entry
4. (Previously, scheduling deliveries)

## FirebaseManager Class

The FirebaseManager class manages the following:

1. FireStore database connection
2. Reading and updating user data
3. Fetching the relevant ***REMOVED*** active subscriptions and schedules

## LogManager/AlertManager/SMTPSHandler Class

The LogManager handles all log files.

The AlertManager is a work in progress that handles sending alerts via services like Slack.

The SMTPSHandler handles sending alerts via e-mail with screenshots of the active session.

## Supervisord & Celery Task Queue & Flower Task Manager

Supervisord manages starting the session, spinning up Celery workers, and the Flower admin portal. It allows parallel processing of task queues.

## WhatsApp CLI & WhatsApp CLI Interface

The WhatsApp CLI is started as a Python subprocess via the WhatsApp CLI interface. This ensures that if there is a memory leak or if the process crashes it doesn't bring down the whole system.

The WhatsApp CLI handles all Selenium tasks and interfaces with the SessionManager to connect to the active driver session.

## WIP: WhatsAppReceive Class

The WhatsAppReceive class is a work in progress. It will handle the reception of WhatsApp messages, the automated replies, and user management. It can be extended in future to handle any task that requires reading of incomming messages. At the moment it is a utility class that is indepedant of the rest of the docker system... it should perhaps be in its own branch.

---

# Wattie v2.0-Docker Deployment

---

Wattie has been moved to a Docker multi-service container - it can now be started quickly without worrying about EC2 environment configuration.

## 1. Docker

`docker-compose up --build`

This will start a Docker container with **port 8001 exposed for API and 5900 exposed for VNC**.

## 2. Graphical VNC Viewer

Using your VNC viewer of choice connect to **localhost port 5900**, the following example uses **TigerVNC**:

`vncviewer localhost:5900`

> Password: 'secret'

## Amazon EC2 Config

Ports 8001 and 5900 need to be open to incoming connections in order to use API and VNC.

## Environment variables

### Host

The following environment variables need to be exported on the Docker host for the build to succeed.

**FIREBASE_CERTIFICATE_PATH**: The path to the directory holding the Firebase certificate e.g. /home/ec2-user/secrets

**FIREBASE_CERTIFICATE_NAME**: The name of the Firebase certificate e.g. ***REMOVED***

**SELENIUM_VNC_PASSWORD**: Password for Selenium VNC server - for now just hard coded as '***REMOVED***' to save time.

**AUTH_TOKEN**: Token to authorize API requests. 'X-Auth-Token' header entry in HTTP request.

e.g. `curl -H "X-Auth-Token: "$AUTH_TOKEN"" ***REMOVED***:8001/health`

This means if the server is rebuilt, the actual Firebase certificate will need to be uploaded using `scp` and the relevant SSH key, for example:

See (Example syntax for Secure Copy)[http://www.hypexr.org/linux_scp_help.php]

`scp -i .ssh/ssh-key /home/yoda/secrets/***REMOVED*** ubuntu@ec2-url.com:~/secrets`

### Docker-compose

**CELL_NUMBER**: The cell number of Wattie - used for health checks.

**MONITOR_FREQUENCY**: How often in seconds to check Wattie's health.

**TIMEOUT**: How long to wait in seconds before refreshing or restarting the connection.

## SSHing into EC2 host

See Wattie v1.0 for instructions.

---

# Wattie v1.0 Deployment

---

# Run locally:

**Start mongo db:** ensure default config set
mongod

**Mongo shell:** database admin
mongo
use db-name
db.collection.action

**Start Session Manager:** whatsapp_cli.py called on separate thread for robustness
source venv/bin/activate
python session_manager.py

# Run on EC2 GRAPHICAL instance:

## Server instance users

There are two users set up:

`ubuntu` is the default EC2 user created when setting up a new EC2 instance - can be used for SSH and terminal tasks.

`wattie` is the user attached to the Linux graphical environment of choice - used when doing graphical tasks.

## SSH into instance

If you don't have an SSH key set up, you may need to do that first, otherwise do the following:

> ssh -i <ssh-key-file> ubuntu@***REMOVED***

## Install Firefox geckodriver

See https://askubuntu.com/questions/870530/how-to-install-geckodriver-in-ubuntu

> sudo apt-get upgrade
> sudo apt-get update
> sudo apt-get install firefox-esr
> curl -O https://github.com/mozilla/geckodriver/releases/download/v0.19.1/geckodriver-v0.19.1-arm7hf.tar.gz
> tar -xzvf geckodriver-v0.19.1-arm7hf.tar.gz
> sudo cp geckodriver /usr/local/bin/

## Configuring mongod service:

You may have to install MongoDB first.

### Create MongoDB service on server

See https://askubuntu.com/questions/748789/run-mongodb-service-as-daemon-of-systemd-on-ubuntu-15-10

Use the --smallfiles option when creating mongod service to stop the daemon from complaining about lack of storage space.

### Configure MongoDB working directories

> sudo mkdir -p /data/db/
> sudo chown `id -u` /data/db

### Start newly created MongoDB service which starts mongod as a daemon

> sudo service mongodb start

## Connecting to VNC Server

First SSH into the instance using the graphical user Wattie:

> ssh -L 5901:127.0.0.1:5901 wattie@***REMOVED***

password: ***REMOVED***

Start the VNC server on extension 1, it may say that it is already running:

> vncserver :1 // starts vncserver on port 5901

Start local VNC viewer and connect to localhost:5901, with password 50Millio

When you close your SSH and VNC connection, Wattie will continue operating in graphical instance.

When in instance, you can switch to graphical wattie user as follows:

> su - wattie

## VNC Viewer complains about security issues

SSH into the instance and run the following command to reset the blacklist. This issue occurs if you enter the wrong VNC server password.

> vncconfig -display :1 -set BlacklistTimeout=0 -set BlacklistThreshold=1000000
