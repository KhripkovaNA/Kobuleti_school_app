from flask import Flask
from config import Config
from sqlalchemy import MetaData
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect


convention = {
    "ix": 'ix_%(column_0_label)s',
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

metadata = MetaData(naming_convention=convention)

app = Flask(__name__)
app.config.from_object(Config)
db = SQLAlchemy(app, metadata=metadata)
csrf = CSRFProtect(app)
migrate = Migrate(app, db, render_as_batch=True)
login = LoginManager(app)
login.login_view = 'auth.login'

from app.auth.routes import auth
app.register_blueprint(auth)

from app.main.routes import main
app.register_blueprint(main)

from app.app_settings.routes import app_settings
app.register_blueprint(app_settings)

from app.finance.routes import finance
app.register_blueprint(finance)

from app.school import school
app.register_blueprint(school)

from app.timetable.routes import timetable
app.register_blueprint(timetable)

from app.school_classes.routes import school_classes
app.register_blueprint(school_classes)

from app.after_school.routes import after_school
app.register_blueprint(after_school)
