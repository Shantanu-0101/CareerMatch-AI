from flask import Blueprint, redirect, render_template, url_for
from flask_login import current_user, login_required
from sqlalchemy import func

from ..extensions import db
from ..models import Activity, InterviewProgress, InterviewQuestion, Job, ResumeAnalysis
from ..services.job_matcher import ranked_jobs, user_skill_set

bp = Blueprint("dashboard", __name__)


@bp.route("/")
def home():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))
    return render_template("landing.html")


@bp.route("/dashboard")
@login_required
def index():
    user = current_user
    analyses = (ResumeAnalysis.query.filter_by(user_id=user.id)
                .order_by(ResumeAnalysis.created_at.asc()).all())
    latest = analyses[-1] if analyses else None
    skills = user_skill_set(user)
    recommended = [r for r in ranked_jobs(user, Job.query.all()) if r[1]["score"] >= 50]

    rows = (db.session.query(InterviewQuestion.domain, func.count(InterviewProgress.id))
            .join(InterviewQuestion, InterviewProgress.question_id == InterviewQuestion.id)
            .filter(InterviewProgress.user_id == user.id, InterviewProgress.skipped.is_(False))
            .group_by(InterviewQuestion.domain).all())

    chart = {
        "categories": {"labels": [c["name"] for c in latest.result["categories"]],
                       "values": [c["percent"] for c in latest.result["categories"]]} if latest else None,
        "history": {"labels": [a.created_at.strftime("%d %b") for a in analyses[-10:]],
                    "values": [a.overall_score for a in analyses[-10:]]} if analyses else None,
        "interview": {"labels": [r[0] for r in rows], "values": [r[1] for r in rows]} if rows else None,
    }
    stats = {
        "resumes": user.resumes.count(),
        "latest_score": latest.overall_score if latest else None,
        "skills": len(skills),
        "recommended_jobs": len(recommended),
        "interview_done": sum(r[1] for r in rows),
        "profile_completion": user.profile.completion if user.profile else 0,
    }
    activities = user.activities.order_by(Activity.created_at.desc()).limit(8).all()
    return render_template("dashboard/index.html", stats=stats, chart=chart, latest=latest,
                           activities=activities, top_jobs=recommended[:3])
