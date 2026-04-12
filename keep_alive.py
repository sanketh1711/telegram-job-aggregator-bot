from flask import Flask
from threading import Thread
import os

app = Flask(__name__)

@app.route('/')
def home():
    return "🚀 Job Alert Bot is alive and running!"

def run():
    # Render assigns a specific port, this grabs it
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    # Runs the web server in a separate thread so it doesn't pause your bot
    t = Thread(target=run)
    t.start()