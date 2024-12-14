from flask import Flask
from config import Config
from sqlalchemy import MetaData
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_caching import Cache

convention = {
    "ix": 'ix_%(column_0_label)s',
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

metadata = MetaData(naming_convention=convention)
db = SQLAlchemy(metadata=metadata)
csrf = CSRFProtect()
migrate = Migrate(render_as_batch=True)
cache = Cache()
login = LoginManager()
login.login_view = 'auth.login'


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    app.config['CACHE_TYPE'] = 'SimpleCache'
    app.config['CACHE_DEFAULT_TIMEOUT'] = 86400

    db.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app, db)
    cache.init_app(app)
    login.init_app(app)

    @app.context_processor
    def inject_sidebar_data():
        from app.caching.service import get_cache_school_subjects, get_cache_school_classes, \
            get_cache_school_attending_students
        return dict(
            school_subjects=get_cache_school_subjects(),
            classes_school=get_cache_school_classes(),
            school_attending_students=get_cache_school_attending_students()
        )

    from app.auth.routes import auth
    app.register_blueprint(auth)

    from app.errors.handlers import errors
    app.register_blueprint(errors)

    from app.main.routes import main
    app.register_blueprint(main)

    from app.app_settings.routes import app_settings
    app.register_blueprint(app_settings)

    from app.finance.routes import finance
    app.register_blueprint(finance)

    from app.school.routes import school
    app.register_blueprint(school)

    from app.timetable.routes import timetable
    app.register_blueprint(timetable)

    from app.school_classes.routes import school_classes
    app.register_blueprint(school_classes)

    from app.after_school.routes import after_school
    app.register_blueprint(after_school)

    return app
