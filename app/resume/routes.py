import os
import re

from flask import (Blueprint, Response, current_app, flash, redirect, render_template, request,
                   send_from_directory, url_for)
from flask_login import current_user, login_required

from ..data.skills import COMPANY_FOCUS, DEFAULT_ROLE, ROLE_SKILLS
from ..extensions import db
from ..models import Resume, ResumeAnalysis, ResumeBuilderData, log_activity
from ..services.pdf_generator import build_pdf
from ..services.resume_analyzer import analyze_resume
from ..services.resume_builder import TEMPLATES, clean_data, default_data
from ..services.resume_parser import ResumeParseError, extract_text, validate_and_save

bp = Blueprint("resume", __name__, url_prefix="/resume")


def _target():
    role = request.form.get("role", DEFAULT_ROLE)
    company = request.form.get("company", "")
    if role not in ROLE_SKILLS:
        role = DEFAULT_ROLE
    if company not in COMPANY_FOCUS:
        company = ""
    return role, company


def _save_analysis(resume, role, company):
    result = analyze_resume(resume.extracted_text, role, company)
    analysis = ResumeAnalysis(resume_id=resume.id, user_id=current_user.id, overall_score=result["overall_score"],
                              method=result["method"], target_role=role, target_company=company, result=result)
    db.session.add(analysis)
    return analysis, result


# ------------------------------------------------------------------ analyzer
@bp.route("/analyzer")
@login_required
def analyzer():
    resumes = current_user.resumes.order_by(Resume.uploaded_at.desc()).all()
    preferred = current_user.profile.preferred_roles.split(",")[0].strip() if current_user.profile and current_user.profile.preferred_roles else ""
    return render_template("resume/analyzer.html", resumes=resumes, roles=list(ROLE_SKILLS),
                           companies=list(COMPANY_FOCUS), default_role=preferred if preferred in ROLE_SKILLS else DEFAULT_ROLE)


@bp.route("/upload", methods=["POST"])
@login_required
def upload():
    role, company = _target()
    folder = current_app.config["UPLOAD_FOLDER"]
    try:
        original, stored, ext = validate_and_save(request.files.get("resume"), folder)
    except ResumeParseError as e:
        flash(str(e), "error")
        return redirect(url_for("resume.analyzer"))
    try:
        text = extract_text(os.path.join(folder, stored), ext)
    except ResumeParseError as e:
        os.remove(os.path.join(folder, stored))
        flash(str(e), "error")
        return redirect(url_for("resume.analyzer"))

    resume = Resume(user_id=current_user.id, original_filename=original, stored_filename=stored,
                    file_type=ext, extracted_text=text)
    db.session.add(resume)
    db.session.flush()
    analysis, result = _save_analysis(resume, role, company)
    log_activity(current_user.id, f"Analyzed resume '{original}' - score {result['overall_score']}/100", "fa-file-lines")
    db.session.commit()
    if result["ai"].get("error"):
        flash(result["ai"]["error"], "warning")
    flash("Resume analyzed successfully.", "success")
    return redirect(url_for("resume.analysis", analysis_id=analysis.id))


@bp.route("/analysis/<int:analysis_id>")
@login_required
def analysis(analysis_id):
    a = ResumeAnalysis.query.filter_by(id=analysis_id, user_id=current_user.id).first_or_404()
    history = a.resume.analyses.all()
    return render_template("resume/analysis.html", a=a, r=a.result, history=history,
                           roles=list(ROLE_SKILLS), companies=list(COMPANY_FOCUS))


@bp.route("/<int:resume_id>/reanalyze", methods=["POST"])
@login_required
def reanalyze(resume_id):
    resume = Resume.query.filter_by(id=resume_id, user_id=current_user.id).first_or_404()
    role, company = _target()
    analysis, result = _save_analysis(resume, role, company)
    log_activity(current_user.id, f"Re-analyzed '{resume.original_filename}' for {role}{' at ' + company if company else ''}",
                 "fa-rotate")
    db.session.commit()
    if result["ai"].get("error"):
        flash(result["ai"]["error"], "warning")
    flash("New analysis created.", "success")
    return redirect(url_for("resume.analysis", analysis_id=analysis.id))


@bp.route("/<int:resume_id>/file")
@login_required
def download_file(resume_id):
    resume = Resume.query.filter_by(id=resume_id, user_id=current_user.id).first_or_404()
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], resume.stored_filename,
                               as_attachment=True, download_name=resume.original_filename)


@bp.route("/<int:resume_id>/delete", methods=["POST"])
@login_required
def delete(resume_id):
    resume = Resume.query.filter_by(id=resume_id, user_id=current_user.id).first_or_404()
    path = os.path.join(current_app.config["UPLOAD_FOLDER"], resume.stored_filename)
    if os.path.exists(path):
        os.remove(path)
    name = resume.original_filename
    db.session.delete(resume)
    db.session.commit()
    flash(f"Deleted '{name}' and its analyses.", "success")
    return redirect(url_for("resume.analyzer"))


# ------------------------------------------------------------------ builder
@bp.route("/builder")
@login_required
def builder_list():
    items = current_user.builder_resumes.order_by(ResumeBuilderData.updated_at.desc()).all()
    return render_template("resume/builder_list.html", items=items, templates=TEMPLATES)


@bp.route("/builder/new")
@login_required
def builder_new():
    return render_template("resume/builder.html", item=None, data=default_data(current_user),
                           title="My Resume", template="modern", templates=TEMPLATES)


@bp.route("/builder/<int:item_id>")
@login_required
def builder_edit(item_id):
    item = ResumeBuilderData.query.filter_by(id=item_id, user_id=current_user.id).first_or_404()
    return render_template("resume/builder.html", item=item, data=item.data, title=item.title,
                           template=item.template, templates=TEMPLATES)


@bp.route("/builder/save", methods=["POST"])
@login_required
def builder_save():
    item_id = request.form.get("item_id", type=int)
    title = " ".join(request.form.get("title", "").split())[:120]
    template = request.form.get("template", "modern")
    if template not in TEMPLATES:
        template = "modern"
    back = url_for("resume.builder_edit", item_id=item_id) if item_id else url_for("resume.builder_new")
    if not title:
        flash("Please give your resume a title.", "error")
        return redirect(back)
    try:
        data = clean_data(request.form.get("data"))
    except ValueError as e:
        flash(str(e), "error")
        return redirect(back)

    if item_id:
        item = ResumeBuilderData.query.filter_by(id=item_id, user_id=current_user.id).first_or_404()
        item.title, item.template, item.data = title, template, data
        log_activity(current_user.id, f"Updated resume '{title}' in the builder", "fa-pen-to-square")
    else:
        item = ResumeBuilderData(user_id=current_user.id, title=title, template=template, data=data)
        db.session.add(item)
        log_activity(current_user.id, f"Created resume '{title}' in the builder", "fa-file-circle-plus")
    db.session.commit()
    flash("Resume saved.", "success")
    if request.form.get("then") == "download":
        # Land on the editor page, which then starts the PDF download (avoids duplicate saves).
        return redirect(url_for("resume.builder_edit", item_id=item.id, download=1))
    return redirect(url_for("resume.builder_edit", item_id=item.id))


@bp.route("/builder/<int:item_id>/pdf")
@login_required
def builder_pdf(item_id):
    item = ResumeBuilderData.query.filter_by(id=item_id, user_id=current_user.id).first_or_404()
    pdf = build_pdf(item.data, item.template)
    filename = re.sub(r"[^A-Za-z0-9_-]+", "_", item.title).strip("_") or "resume"
    return Response(pdf, mimetype="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{filename}.pdf"'})


@bp.route("/builder/<int:item_id>/delete", methods=["POST"])
@login_required
def builder_delete(item_id):
    item = ResumeBuilderData.query.filter_by(id=item_id, user_id=current_user.id).first_or_404()
    db.session.delete(item)
    db.session.commit()
    flash("Resume deleted.", "success")
    return redirect(url_for("resume.builder_list"))
