import random

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required
from sqlalchemy import func

from ..data.question_bank import DIFFICULTIES, DOMAINS
from ..extensions import db
from ..models import InterviewProgress, InterviewQuestion, log_activity
from ..services.ai_service import AIError, get_ai
from ..services.interview_service import evaluate

bp = Blueprint("interview", __name__, url_prefix="/interview")

COUNTS = [3, 5, 10]


def _visible(q):
    return q is not None and (q.user_id is None or q.user_id == current_user.id)


@bp.route("/")
@login_required
def index():
    uid = current_user.id
    done = dict(db.session.query(InterviewQuestion.domain, func.count(func.distinct(InterviewProgress.question_id)))
                .join(InterviewQuestion, InterviewProgress.question_id == InterviewQuestion.id)
                .filter(InterviewProgress.user_id == uid, InterviewProgress.skipped.is_(False))
                .group_by(InterviewQuestion.domain).all())
    totals = dict(db.session.query(InterviewQuestion.domain, func.count(InterviewQuestion.id))
                  .filter(InterviewQuestion.source == "bank").group_by(InterviewQuestion.domain).all())
    domain_stats = [{"domain": d, "done": done.get(d, 0), "total": totals.get(d, 0)} for d in DOMAINS]
    recent = (current_user.interview_progress.order_by(InterviewProgress.completed_at.desc()).limit(10).all())
    scored = [p.score for p in current_user.interview_progress.filter(InterviewProgress.score.isnot(None))]
    avg = round(sum(scored) / len(scored), 1) if scored else None
    return render_template("interview/index.html", domains=DOMAINS, difficulties=DIFFICULTIES, counts=COUNTS,
                           domain_stats=domain_stats, recent=recent, avg=avg, active=session.get("iv"))


@bp.route("/start", methods=["POST"])
@login_required
def start():
    domain = request.form.get("domain")
    difficulty = request.form.get("difficulty")
    count = request.form.get("count", type=int)
    mode = request.form.get("mode", "bank")
    if domain not in DOMAINS or difficulty not in DIFFICULTIES or count not in COUNTS:
        flash("Please choose a valid domain, difficulty and number of questions.", "error")
        return redirect(url_for("interview.index"))

    ids = []
    if mode == "ai" and domain != "HR":
        ai = get_ai()
        if not ai.enabled:
            flash("AI is not configured, so questions come from the curated question bank.", "warning")
        else:
            try:
                for item in ai.generate_questions(domain, difficulty, count):
                    q = InterviewQuestion(domain=domain, difficulty=difficulty, source="ai",
                                          user_id=current_user.id, **item)
                    db.session.add(q)
                    db.session.flush()
                    ids.append(q.id)
            except AIError as e:
                db.session.rollback()
                ids = []
                flash(f"{e} Using the curated question bank instead.", "warning")

    if not ids:
        mode = "bank"
        q = InterviewQuestion.query.filter_by(domain=domain, source="bank")
        if domain != "HR":
            q = q.filter_by(difficulty=difficulty)
        pool = q.all()
        answered = {p.question_id for p in current_user.interview_progress.filter_by(skipped=False)}
        fresh = [x for x in pool if x.id not in answered]
        old = [x for x in pool if x.id in answered]
        random.shuffle(fresh)
        random.shuffle(old)
        ids = [x.id for x in (fresh + old)[:count]]
        if not ids:
            flash("No questions available for that selection.", "error")
            return redirect(url_for("interview.index"))
        if len(ids) < count:
            flash(f"Only {len(ids)} question(s) are available for this selection.", "info")

    session["iv"] = {"ids": ids, "index": 0, "progress": [], "domain": domain,
                     "difficulty": "All levels" if domain == "HR" else difficulty, "mode": mode}
    log_activity(current_user.id, f"Started {domain} interview practice ({len(ids)} questions)", "fa-microphone")
    db.session.commit()
    return redirect(url_for("interview.practice"))


@bp.route("/practice")
@login_required
def practice():
    iv = session.get("iv")
    if not iv:
        return redirect(url_for("interview.index"))
    if iv["index"] >= len(iv["ids"]):
        return redirect(url_for("interview.summary"))
    q = db.session.get(InterviewQuestion, iv["ids"][iv["index"]])
    if not _visible(q):
        session.pop("iv", None)
        flash("That practice session is no longer available.", "error")
        return redirect(url_for("interview.index"))
    return render_template("interview/practice.html", q=q, iv=iv, number=iv["index"] + 1, total=len(iv["ids"]))


@bp.route("/answer", methods=["POST"])
@login_required
def answer():
    iv = session.get("iv")
    if not iv or iv["index"] >= len(iv["ids"]):
        return redirect(url_for("interview.index"))
    q = db.session.get(InterviewQuestion, iv["ids"][iv["index"]])
    if not _visible(q):
        return redirect(url_for("interview.index"))
    text = request.form.get("answer", "").strip()[:5000]
    skip = request.form.get("action") == "skip"
    if not skip and len(text) < 3:
        flash("Please write an answer, or choose 'Skip & show answer'.", "error")
        return redirect(url_for("interview.practice"))

    if skip:
        p = InterviewProgress(user_id=current_user.id, question_id=q.id, skipped=True, method="rule")
    else:
        result, method = evaluate(q.question, q.answer, text)
        p = InterviewProgress(user_id=current_user.id, question_id=q.id, user_answer=text,
                              score=result["score"], feedback=result, method=method)
        if result.get("ai_error"):
            flash(f"{result['ai_error']} Used keyword-based evaluation.", "warning")
    db.session.add(p)
    db.session.commit()
    iv["progress"].append(p.id)
    session.modified = True
    return redirect(url_for("interview.review", progress_id=p.id))


@bp.route("/review/<int:progress_id>")
@login_required
def review(progress_id):
    p = InterviewProgress.query.filter_by(id=progress_id, user_id=current_user.id).first_or_404()
    iv = session.get("iv")
    in_session = bool(iv and progress_id in iv.get("progress", []))
    is_last = in_session and iv["index"] + 1 >= len(iv["ids"])
    return render_template("interview/review.html", p=p, q=p.question, in_session=in_session, is_last=is_last,
                           iv=iv)


@bp.route("/next", methods=["POST"])
@login_required
def next_question():
    iv = session.get("iv")
    if not iv:
        return redirect(url_for("interview.index"))
    iv["index"] += 1
    session.modified = True
    if iv["index"] >= len(iv["ids"]):
        return redirect(url_for("interview.summary"))
    return redirect(url_for("interview.practice"))


@bp.route("/summary")
@login_required
def summary():
    iv = session.get("iv")
    if not iv:
        return redirect(url_for("interview.index"))
    rows = (InterviewProgress.query.filter(InterviewProgress.id.in_(iv["progress"]),
                                           InterviewProgress.user_id == current_user.id).all())
    scored = [r.score for r in rows if r.score is not None]
    return render_template("interview/summary.html", rows=rows, iv=iv,
                           avg=round(sum(scored) / len(scored), 1) if scored else None)


@bp.route("/end", methods=["POST"])
@login_required
def end():
    session.pop("iv", None)
    flash("Practice session ended.", "info")
    return redirect(url_for("interview.index"))


@bp.route("/history")
@login_required
def history():
    domain = request.args.get("domain", "")
    q = current_user.interview_progress.join(InterviewQuestion)
    if domain in DOMAINS:
        q = q.filter(InterviewQuestion.domain == domain)
    rows = q.order_by(InterviewProgress.completed_at.desc()).limit(100).all()
    return render_template("interview/history.html", rows=rows, domains=DOMAINS, domain=domain)
