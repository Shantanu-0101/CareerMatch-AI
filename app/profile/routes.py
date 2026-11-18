from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..data.skills import EXPERIENCE_LEVELS, ROLE_SKILLS, SKILLS
from ..extensions import db
from ..models import UserProfile, log_activity, split_csv

bp = Blueprint("profile", __name__, url_prefix="/profile")

LIMITS = {"phone": 30, "location": 120, "headline": 160, "education": 2000, "skills": 1000,
          "career_interests": 1000, "preferred_roles": 500, "preferred_locations": 500}


@bp.route("/", methods=["GET", "POST"])
@login_required
def index():
    profile = current_user.profile
    if profile is None:
        profile = UserProfile(user_id=current_user.id)
        db.session.add(profile)
        db.session.commit()

    if request.method == "POST":
        full_name = " ".join(request.form.get("full_name", "").split())
        errors = []
        if not 2 <= len(full_name) <= 120:
            errors.append("Full name must be 2-120 characters.")
        level = request.form.get("experience_level", "")
        if level and level not in EXPERIENCE_LEVELS:
            errors.append("Please choose a valid experience level.")
        values = {}
        for field, limit in LIMITS.items():
            value = request.form.get(field, "").strip()
            if len(value) > limit:
                errors.append(f"{field.replace('_', ' ').title()} is too long (max {limit} characters).")
            values[field] = value
        if errors:
            for e in errors:
                flash(e, "error")
        else:
            current_user.full_name = full_name
            for field in ("skills", "preferred_roles", "preferred_locations"):
                values[field] = ", ".join(split_csv(values[field]))
            for field, value in values.items():
                setattr(profile, field, value)
            profile.experience_level = level
            log_activity(current_user.id, "Updated your profile", "fa-user-pen")
            db.session.commit()
            flash("Profile updated.", "success")
            return redirect(url_for("profile.index"))

    return render_template("profile/index.html", profile=profile, levels=EXPERIENCE_LEVELS,
                           roles=list(ROLE_SKILLS), skill_suggestions=sorted(list(SKILLS) + ["C"]))
