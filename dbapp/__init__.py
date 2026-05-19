import random, string, threading
import logging
from functools import wraps
from flask import Flask, abort, render_template

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s',
)
logger = logging.getLogger(__name__)
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user
from flask_marshmallow import Marshmallow
from flask_session import Session
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash
from .config import ConfigWatcher

app = Flask(__name__)

config_watcher = ConfigWatcher(app)
config_thread = threading.Thread(target=config_watcher.run, daemon=True)
config_thread.start()

Session(app)

db = SQLAlchemy(app)
ma = Marshmallow(app)
migrate = Migrate(app, db, render_as_batch=True)

from .models import tables

login_manager = LoginManager()
login_manager.login_view = 'auth_bp.login'
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(tables.USERS, str(user_id))


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.has_role('Admin'):
            abort(403)
        return f(*args, **kwargs)
    return decorated


from dbapp.views.user import user_bp
app.register_blueprint(user_bp, url_prefix='/')

from dbapp.views.api import api
app.register_blueprint(api, url_prefix='/api')

from dbapp.views.auth import auth
app.register_blueprint(auth)

from dbapp.views.admin import admin_bp
app.register_blueprint(admin_bp, url_prefix='/admin')

from dbapp.views.studies import studies_bp
app.register_blueprint(studies_bp, url_prefix='/')

from dbapp.views.files import files_bp
app.register_blueprint(files_bp, url_prefix='/')

from dbapp.views.dashboard import dashboard_bp
app.register_blueprint(dashboard_bp, url_prefix='/')


@app.errorhandler(404)
def notfound(_error):
    return render_template('errors/404.jinja2'), 404


def generate_error_id():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=16))


@app.errorhandler(500)
def internalError(error):
    error_id = generate_error_id()
    logger.error("Internal server error %s", error_id, exc_info=True)
    return render_template('errors/500.jinja2', error_id=error_id), 500


@app.errorhandler(403)
def forbidden(_error):
    return render_template('errors/403.jinja2'), 403


def _init_db():
    try:
        tables.USERS.query.filter(tables.USERS.name == "admin").one_or_none()
    except Exception:
        db.create_all()
        admin_role = tables.ROLES(name='Admin')
        db.session.add(admin_role)
        db.session.commit()
        student_role = tables.ROLES(name='Student')
        db.session.add(student_role)
        db.session.commit()
        admin = tables.USERS(
            name='admin',
            display_name='Administrator',
            password=generate_password_hash('password')
        )
        admin.roles = [admin_role, student_role]
        db.session.add(admin)
        db.session.commit()


with app.app_context():
    _init_db()

from .tools import clean_html
from .tools import convertMarkdown


@app.context_processor
def global_variables():
    newslist = tables.NEWS.query.order_by(tables.NEWS.create_at.desc()).limit(5)
    title = config_watcher.get_config()['title']
    return {
        'newslist': newslist,
        'TITLE': title,
        'clean_html': clean_html,
        'convertMarkdown': convertMarkdown
    }
