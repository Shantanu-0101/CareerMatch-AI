from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..data.skills import EXPERIENCE_LEVELS, JOB_TYPES
from ..extensions import db
from ..models import Job, SavedJob, log_activity
from ..services.job_matcher import LocalJobSource, ranked_jobs, user_skill_set

bp = Blueprint("jobs", __name__, url_prefix="/jobs")

job_source = LocalJobSource()


@bp.route("/")
@login_required
def index():
    filters = {k: request.args.get(k, "").strip()[:100] for k in ("title", "skills", "location", "experience", "job_type")}
    jobs = job_source.search(**filters)
    results = ranked_jobs(current_user, jobs)
    saved_ids = {s.job_id for s in current_user.saved_jobs}
    locations = sorted({j.location for j in Job.query.with_entities(Job.location)})
    return render_template("jobs/index.html", results=results, filters=filters, saved_ids=saved_ids,
                           levels=EXPERIENCE_LEVELS, job_types=JOB_TYPES, locations=locations,
                           my_skills=user_skill_set(current_user))


@bp.route("/saved")
@login_required
def saved():
    saved_rows = current_user.saved_jobs.order_by(SavedJob.saved_at.desc()).all()
    results = ranked_jobs(current_user, [s.job for s in saved_rows])
    return render_template("jobs/saved.html", results=results, saved_ids={s.job_id for s in saved_rows})


@bp.route("/<int:job_id>/save", methods=["POST"])
@login_required
def toggle_save(job_id):
    job = db.get_or_404(Job, job_id)
    existing = SavedJob.query.filter_by(user_id=current_user.id, job_id=job.id).first()
    if existing:
        db.session.delete(existing)
        flash(f"Removed '{job.title}' from saved jobs.", "info")
    else:
        db.session.add(SavedJob(user_id=current_user.id, job_id=job.id))
        log_activity(current_user.id, f"Saved job '{job.title}' at {job.company}", "fa-bookmark")
        flash(f"Saved '{job.title}'.", "success")
    db.session.commit()
    nxt = request.form.get("next", "")
    return redirect(nxt if nxt.startswith("/") and not nxt.startswith("//") else url_for("jobs.index"))
