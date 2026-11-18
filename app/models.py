"""Database models (SQLite via SQLAlchemy)."""
from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db, login_manager


def now():
    return datetime.now()


def split_csv(text):
    """'Python, SQL ,Git' -> ['Python', 'SQL', 'Git'] (no blanks, no duplicates)."""
    seen, out = set(), []
    for part in (text or "").split(","):
        item = part.strip()
        if item and item.lower() not in seen:
            seen.add(item.lower())
            out.append(item)
    return out


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=now)

    profile = db.relationship("UserProfile", backref="user", uselist=False, cascade="all, delete-orphan")
    resumes = db.relationship("Resume", backref="user", lazy="dynamic", cascade="all, delete-orphan")
    builder_resumes = db.relationship("ResumeBuilderData", backref="user", lazy="dynamic", cascade="all, delete-orphan")
    saved_jobs = db.relationship("SavedJob", backref="user", lazy="dynamic", cascade="all, delete-orphan")
    interview_progress = db.relationship("InterviewProgress", backref="user", lazy="dynamic", cascade="all, delete-orphan")
    activities = db.relationship("Activity", backref="user", lazy="dynamic", cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def first_name(self):
        return self.full_name.split()[0] if self.full_name else ""


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


class UserProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), unique=True, nullable=False)
    phone = db.Column(db.String(30), default="")
    location = db.Column(db.String(120), default="")
    headline = db.Column(db.String(160), default="")
    education = db.Column(db.Text, default="")
    skills = db.Column(db.Text, default="")  # comma separated
    career_interests = db.Column(db.Text, default="")
    preferred_roles = db.Column(db.Text, default="")  # comma separated
    preferred_locations = db.Column(db.Text, default="")  # comma separated
    experience_level = db.Column(db.String(40), default="")
    updated_at = db.Column(db.DateTime, default=now, onupdate=now)

    @property
    def skill_list(self):
        return split_csv(self.skills)

    @property
    def completion(self):
        fields = [self.phone, self.location, self.headline, self.education, self.skills,
                  self.career_interests, self.preferred_roles, self.preferred_locations, self.experience_level]
        return round(100 * sum(1 for f in fields if f and f.strip()) / len(fields))


class Resume(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=False, unique=True)
    file_type = db.Column(db.String(10), nullable=False)
    extracted_text = db.Column(db.Text, default="")
    uploaded_at = db.Column(db.DateTime, default=now)

    analyses = db.relationship("ResumeAnalysis", backref="resume", lazy="dynamic",
                               cascade="all, delete-orphan", order_by="ResumeAnalysis.created_at.desc()")

    @property
    def latest_analysis(self):
        return self.analyses.first()


class ResumeAnalysis(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    resume_id = db.Column(db.Integer, db.ForeignKey("resume.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    overall_score = db.Column(db.Integer, nullable=False)
    method = db.Column(db.String(10), nullable=False)  # "ai" (rubric + AI feedback) or "rule"
    target_company = db.Column(db.String(60), default="")
    target_role = db.Column(db.String(80), default="")
    result = db.Column(db.JSON, nullable=False)  # full structured result
    created_at = db.Column(db.DateTime, default=now)


class ResumeBuilderData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    title = db.Column(db.String(120), nullable=False)
    template = db.Column(db.String(20), default="modern")
    data = db.Column(db.JSON, nullable=False)
    created_at = db.Column(db.DateTime, default=now)
    updated_at = db.Column(db.DateTime, default=now, onupdate=now)


class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    company = db.Column(db.String(120), nullable=False)
    location = db.Column(db.String(120), nullable=False)
    job_type = db.Column(db.String(40), nullable=False)
    experience_level = db.Column(db.String(40), nullable=False)
    skills = db.Column(db.Text, nullable=False)  # comma separated
    description = db.Column(db.Text, nullable=False)
    salary_range = db.Column(db.String(60), default="")
    # Data source label. "sample" = demonstration data shipped with the app.
    source = db.Column(db.String(40), default="sample")
    created_at = db.Column(db.DateTime, default=now)

    @property
    def skill_list(self):
        return split_csv(self.skills)

    @property
    def is_sample(self):
        return self.source == "sample"


class SavedJob(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    job_id = db.Column(db.Integer, db.ForeignKey("job.id"), nullable=False)
    saved_at = db.Column(db.DateTime, default=now)
    job = db.relationship("Job")
    __table_args__ = (db.UniqueConstraint("user_id", "job_id", name="uq_user_job"),)


class InterviewQuestion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    domain = db.Column(db.String(60), nullable=False, index=True)
    difficulty = db.Column(db.String(20), nullable=False)
    question = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text, nullable=False)
    explanation = db.Column(db.Text, default="")
    source = db.Column(db.String(10), default="bank")  # "bank" (curated) or "ai"
    # AI questions belong to the user who generated them; bank questions are shared (NULL).
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)


class InterviewProgress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    question_id = db.Column(db.Integer, db.ForeignKey("interview_question.id"), nullable=False)
    user_answer = db.Column(db.Text, default="")
    skipped = db.Column(db.Boolean, default=False)
    score = db.Column(db.Integer, nullable=True)  # out of 10
    feedback = db.Column(db.JSON, nullable=True)
    method = db.Column(db.String(10), default="rule")
    completed_at = db.Column(db.DateTime, default=now)
    question = db.relationship("InterviewQuestion")


class Activity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    message = db.Column(db.String(255), nullable=False)
    icon = db.Column(db.String(40), default="fa-circle")
    created_at = db.Column(db.DateTime, default=now)


def log_activity(user_id, message, icon="fa-circle"):
    db.session.add(Activity(user_id=user_id, message=message[:255], icon=icon))
