from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from config import Config

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message_category = "warning"

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    from app.models import User

    @login_manager.user_loader
    def load_user(uid):
        return db.session.get(User, int(uid))

    from app.routes.auth import auth_bp
    from app.routes.dashboard import dash_bp
    from app.routes.academic import acad_bp
    from app.routes.student_portal import stud_bp
    from app.routes.admin_portal import admin_bp
    from app.routes.library_portal import lib_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dash_bp)
    app.register_blueprint(acad_bp)
    app.register_blueprint(stud_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(lib_bp)

    return app
