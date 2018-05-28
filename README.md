selenium-whatsapp

## Run locally:

**Start mongo db:** ensure default config set
mongod

**Mongo shell:** database admin
mongo
use db-name
db.collection.action

**Start Session Manager:** whatsapp_cli.py called on separate thread for robustness
source venv/bin/activate
python session_manager.py
