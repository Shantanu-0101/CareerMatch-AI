import re
from urllib.parse import urlparse

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from ..extensions import db
from ..models import User, UserProfile, log_activity

bp = Blueprint("auth", __name__)

EMAIL_RE = re.compile(r"^[\w.+-]+@[\w-]+(\.[\w-]+)+$")


def _safe_next(target):
    if target and not urlparse(target).netloc and target.startswith("/"):
        return target
    return url_for("dashboard.index")


@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))
    form = {"full_name": "", "email": ""}
    if request.method == "POST":
        full_name = " ".join(request.form.get("full_name", "").split())
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        form = {"full_name": full_name, "email": email}

        errors = []
        if len(full_name) < 2 or len(full_name) > 120:
            errors.append("Please enter your full name (2-120 characters).")
        if not EMAIL_RE.match(email) or len(email) > 120:
            errors.append("Please enter a valid email address.")
        if len(password) < 8 or not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
            errors.append("Password must be at least 8 characters and contain letters and numbers.")
        if password != confirm:
            errors.append("Passwords do not match.")
        if not errors and User.query.filter_by(email=email).first():
            errors.append("An account with this email already exists. Please log in.")

        if errors:
            for e in errors:
                flash(e, "error")
        else:
            user = User(full_name=full_name, email=email)
            user.set_password(password)
            user.profile = UserProfile()
            db.session.add(user)
            db.session.flush()
            log_activity(user.id, "Created your Career Match AI account", "fa-user-plus")
            db.session.commit()
            login_user(user)
            flash(f"Welcome, {user.first_name}! Complete your profile for better recommendations.", "success")
            return redirect(url_for("dashboard.index"))
    return render_template("auth/register.html", form=form)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))
    email = ""
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user, remember=bool(request.form.get("remember")))
            flash(f"Welcome back, {user.first_name}!", "success")
            return redirect(_safe_next(request.args.get("next")))
        flash("Invalid email or password.", "error")
    return render_template("auth/login.html", email=email)


@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))
