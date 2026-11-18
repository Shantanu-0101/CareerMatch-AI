"""Seeds demonstration jobs and the curated interview question bank (only when tables are empty)."""
from .data.question_bank import HR_QUESTIONS, QUESTION_BANK
from .data.sample_jobs import SAMPLE_JOBS
from .extensions import db
from .models import InterviewQuestion, Job


def seed_database():
    if Job.query.count() == 0:
        for j in SAMPLE_JOBS:
            db.session.add(Job(source="sample", **j))

    if InterviewQuestion.query.filter_by(source="bank").count() == 0:
        for domain, levels in QUESTION_BANK.items():
            for difficulty, items in levels.items():
                for q, a, e in items:
                    db.session.add(InterviewQuestion(domain=domain, difficulty=difficulty, question=q,
                                                     answer=a, explanation=e, source="bank"))
        for q, a, e in HR_QUESTIONS:
            db.session.add(InterviewQuestion(domain="HR", difficulty="All levels", question=q,
                                             answer=a, explanation=e, source="bank"))
    db.session.commit()
