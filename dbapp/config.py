import os
import time
import yaml
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from flask_session import Session
from datetime import timedelta
from redis import Redis


class ConfigWatcher:
    def __init__(self, app):
        self.app = app

        self.app.config['SESSION_REDIS'] = None
        self.app.config['SESSION_TYPE'] = 'redis'
        self.app.config['SESSION_PERMANENT'] = False
        self.app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=10)

        self.app.config['WTF_CSRF_ENABLED'] = True
        self.app.config['SECRET_KEY'] = os.urandom(32)

        # JSONエンコーディング時に非ASCII文字をエスケープしない
        self.app.json.ensure_ascii = False

        self.config_path = os.path.join(os.getcwd(), "config", "config.yml")

        self.load_config()

        self.event_handler = FileSystemEventHandler()
        self.event_handler.on_modified = self.on_modified
        self.observer = Observer()
        self.observer.schedule(self.event_handler, path=os.path.dirname(self.config_path), recursive=False)
        self.observer.start()

    def load_config(self):
        with open(self.config_path, encoding="utf8") as file:
            config = yaml.safe_load(file)
            self.config = config
            debug = config['Flask']['Debug']
            uli = 'sqlite:///project.db' if config['database'] == 'SQLite' else \
                'mysql+pymysql://{user}:{password}@{host}/{db_name}?charset=utf8mb4'.format(**{
                    'user': config['MySQL']['username'],
                    'password': config['MySQL']['password'],
                    'host': config['MySQL']['host'],
                    'db_name': config['MySQL']['dbname']
                })
            self.app.config['DEBUG'] = debug
            self.app.config['SQLALCHEMY_DATABASE_URI'] = uli
            self.app.config['UPLOAD_FOLDER'] = config['SaveDir']
            self.app.config['SESSION_REDIS'] = Redis(host=config['Redis']['host'], port=int(config['Redis']['port']), password=config['Redis']['password'])

    def on_modified(self, event):
        print("config.yml has been modified. Reloading configuration...")
        self.load_config()

    def run(self):
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.observer.stop()
        self.observer.join()

    def get_config(self):
        return self.config


if __name__ == "__main__":
    config_watcher = ConfigWatcher()
    config_watcher.run()
