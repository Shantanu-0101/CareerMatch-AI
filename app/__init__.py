"""Career Match AI - Flask application factory."""
import os

from flask import Flask, flash, redirect, render_template, request, url_for
from flask_wtf.csrf import CSRFError

from config import Config

from .extensions import csrf, db, login_manager


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(os.path.join(os.path.dirname(app.root_path), "instance"), exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    from .auth.routes import bp as auth_bp
    from .dashboard.routes import bp as dashboard_bp
    from .interview.routes import bp as interview_bp
    from .jobs.routes import bp as jobs_bp
    from .profile.routes import bp as profile_bp
    from .resume.routes import bp as resume_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(resume_bp)
    app.register_blueprint(jobs_bp)
    app.register_blueprint(interview_bp)
    app.register_blueprint(profile_bp)

    register_error_handlers(app)

    @app.context_processor
    def inject_globals():
        from .services.ai_service import get_ai
        return {"ai_enabled": get_ai().enabled, "ai_label": get_ai().label}

    with app.app_context():
        from . import models  # noqa: F401  (register models)
        from .seed import seed_database
        db.create_all()
        seed_database()

    return app


def register_error_handlers(app):
    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/error.html", code=404, title="Page not found",
                               message="The page you are looking for does not exist or you do not have access to it."), 404

    @app.errorhandler(413)
    def too_large(e):
        limit = app.config["MAX_CONTENT_LENGTH"] // (1024 * 1024)
        flash(f"File is too large. The maximum upload size is {limit} MB.", "error")
        return redirect(url_for("resume.analyzer"))

    @app.errorhandler(CSRFError)
    def csrf_error(e):
        flash("Your session expired or the form was invalid. Please try again.", "error")
        return redirect(request.referrer or url_for("dashboard.index"))

    @app.errorhandler(500)
    def server_error(e):
        db.session.rollback()
        return render_template("errors/error.html", code=500, title="Something went wrong",
                               message="An unexpected error occurred. Please try again."), 500
