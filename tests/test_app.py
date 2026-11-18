"""End-to-end tests. Run with:  python -m unittest discover -s tests -v"""
import os
import re
import shutil
import tempfile
import unittest
import warnings
from io import BytesIO

from flask import g

from app import create_app
from app.extensions import db
from app.models import InterviewProgress, Resume, ResumeAnalysis, ResumeBuilderData, SavedJob, User
from config import TestConfig

from .helpers import sample_docx_bytes, sample_pdf_bytes


class BaseCase(unittest.TestCase):
    def setUp(self):
        self.upload_dir = tempfile.mkdtemp()

        class Cfg(TestConfig):
            UPLOAD_FOLDER = self.upload_dir

        warnings.simplefilter("ignore", ResourceWarning)
        self.app = create_app(Cfg)

        # The test keeps one app context open (so tests can query the DB), which would make
        # Flask-Login's per-context user cache leak between test clients. Real requests each
        # get a fresh context, so clear the cache to behave the same way.
        @self.app.before_request
        def _fresh_login_cache():
            g.pop("_login_user", None)

        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()
        shutil.rmtree(self.upload_dir, ignore_errors=True)

    def register(self, email="priya@example.com", name="Priya Sharma", password="secret123", client=None):
        return (client or self.client).post("/register", data={
            "full_name": name, "email": email, "password": password, "confirm_password": password,
        }, follow_redirects=True)

    def upload(self, data, filename, role="Python Developer", company="TCS", client=None):
        return (client or self.client).post("/resume/upload", data={
            "resume": (BytesIO(data), filename), "role": role, "company": company,
        }, content_type="multipart/form-data", follow_redirects=True)


class AuthTests(BaseCase):
    def test_register_login_logout(self):
        r = self.register()
        self.assertIn(b"Welcome back, Priya", r.data)
        user = User.query.filter_by(email="priya@example.com").one()
        self.assertNotEqual(user.password_hash, "secret123")  # hashed
        self.assertIsNotNone(user.profile)
        self.client.post("/logout")
        r = self.client.get("/dashboard")
        self.assertEqual(r.status_code, 302)
        r = self.client.post("/login", data={"email": "priya@example.com", "password": "secret123"}, follow_redirects=True)
        self.assertIn(b"Dashboard", r.data)

    def test_register_validation(self):
        r = self.client.post("/register", data={"full_name": "A", "email": "bad", "password": "short",
                                                "confirm_password": "x"}, follow_redirects=True)
        self.assertIn(b"valid email", r.data)
        self.assertEqual(User.query.count(), 0)

    def test_duplicate_email_and_wrong_password(self):
        self.register()
        self.client.post("/logout")
        r = self.register()
        self.assertIn(b"already exists", r.data)
        r = self.client.post("/login", data={"email": "priya@example.com", "password": "wrong"}, follow_redirects=True)
        self.assertIn(b"Invalid email or password", r.data)

    def test_protected_routes_redirect(self):
        for url in ["/dashboard", "/resume/analyzer", "/resume/builder", "/jobs/", "/interview/", "/profile/"]:
            r = self.client.get(url)
            self.assertEqual(r.status_code, 302, url)
            self.assertIn("/login", r.headers["Location"])

    def test_open_redirect_blocked(self):
        self.register()
        self.client.post("/logout")
        r = self.client.post("/login?next=https://evil.example.com", data={"email": "priya@example.com", "password": "secret123"})
        self.assertTrue(r.headers["Location"].endswith("/dashboard"))


class ResumeTests(BaseCase):
    def test_docx_upload_and_analysis(self):
        self.register()
        r = self.upload(sample_docx_bytes(), "priya.docx")
        self.assertEqual(r.status_code, 200)
        a = ResumeAnalysis.query.one()
        res = a.result
        self.assertEqual(a.method, "rule")
        self.assertTrue(0 <= a.overall_score <= 100)
        self.assertEqual(sum(c["max"] for c in res["categories"]), 100)
        for skill in ["Python", "Flask", "SQL", "Git", "C"]:
            self.assertIn(skill, res["detected_skills"])
        self.assertNotIn("Java", res["detected_skills"])  # JavaScript must not count as Java
        self.assertEqual(res["personal_info"]["email"], "priya.sharma@example.com")
        self.assertIn("Projects", res["sections_found"])
        self.assertIn("REST APIs", res["skill_gap"]["missing"])
        self.assertIn("Communication", res["skill_gap"]["required"])  # TCS focus skill
        self.assertGreaterEqual(a.overall_score, 60)
        self.assertIn(b"Score: rule-based rubric", r.data)

    def test_pdf_upload(self):
        self.register()
        self.upload(sample_pdf_bytes(), "priya.pdf")
        a = ResumeAnalysis.query.one()
        self.assertIn("Python", a.result["detected_skills"])
        self.assertTrue(os.path.exists(os.path.join(self.upload_dir, a.resume.stored_filename)))

    def test_rejects_bad_files(self):
        self.register()
        r = self.upload(b"hello", "notes.txt")
        self.assertIn(b"Only PDF and DOCX", r.data)
        r = self.upload(b"not a real pdf", "fake.pdf")
        self.assertIn(b"not a valid PDF", r.data)
        self.assertEqual(Resume.query.count(), 0)
        self.assertEqual(os.listdir(self.upload_dir), [])

    def test_weak_resume_scores_low_and_gets_suggestions(self):
        self.register()
        self.upload(sample_docx_bytes(["John Doe", "I like computers and want a job in IT. " * 3]), "weak.docx")
        a = ResumeAnalysis.query.one()
        self.assertLess(a.overall_score, 25)
        self.assertTrue(a.result["suggestions"])
        self.assertIn("Projects", a.result["missing_sections"])

    def test_reanalyze_download_delete(self):
        self.register()
        self.upload(sample_docx_bytes(), "priya.docx")
        resume = Resume.query.one()
        r = self.client.post(f"/resume/{resume.id}/reanalyze", data={"role": "Data Analyst", "company": "Google"},
                             follow_redirects=True)
        self.assertIn(b"Data Analyst", r.data)
        self.assertEqual(ResumeAnalysis.query.count(), 2)
        r = self.client.get(f"/resume/{resume.id}/file")
        self.assertEqual(r.status_code, 200)
        self.assertIn("attachment", r.headers["Content-Disposition"])
        r.close()
        self.client.post(f"/resume/{resume.id}/delete")
        self.assertEqual(Resume.query.count(), 0)
        self.assertEqual(ResumeAnalysis.query.count(), 0)

    def test_users_cannot_see_each_others_resumes(self):
        self.register()
        self.upload(sample_docx_bytes(), "priya.docx")
        resume = Resume.query.one()
        analysis = ResumeAnalysis.query.one()
        other = self.app.test_client()
        self.register(email="rahul@example.com", name="Rahul Verma", client=other)
        self.assertEqual(other.get(f"/resume/analysis/{analysis.id}").status_code, 404)
        self.assertEqual(other.get(f"/resume/{resume.id}/file").status_code, 404)
        self.assertEqual(other.post(f"/resume/{resume.id}/delete").status_code, 404)
        self.assertNotIn(b"priya.docx", other.get("/resume/analyzer").data)


class BuilderTests(BaseCase):
    def test_builder_save_edit_pdf(self):
        import json
        self.register()
        self.assertEqual(self.client.get("/resume/builder/new").status_code, 200)
        data = {"personal": {"full_name": "Priya Sharma", "email": "priya@example.com"},
                "summary": "Aspiring <b>developer</b>", "skills": "Python, Flask",
                "education": [{"degree": "B.Tech", "institution": "ABC", "year": "2025", "score": "8.4"}],
                "projects": [{"title": "Career Match AI", "tech": "Flask", "link": "", "description": "Built it\nTested it"}],
                "experience": [], "certifications": [], "achievements": [{"text": "Hackathon winner"}],
                "languages": "English", "hidden": ["languages"], "evil": "ignored"}
        for template in ["modern", "classic", "compact"]:
            r = self.client.post("/resume/builder/save", data={"title": f"CV {template}", "template": template,
                                                               "data": json.dumps(data)})
            self.assertEqual(r.status_code, 302)
        item = ResumeBuilderData.query.filter_by(title="CV classic").one()
        self.assertNotIn("evil", item.data)
        self.assertEqual(item.data["hidden"], ["languages"])
        for it in ResumeBuilderData.query.all():
            r = self.client.get(f"/resume/builder/{it.id}/pdf")
            self.assertEqual(r.mimetype, "application/pdf")
            self.assertTrue(r.data.startswith(b"%PDF"))
        r = self.client.post("/resume/builder/save", data={"item_id": item.id, "title": "Renamed", "template": "modern",
                                                           "data": json.dumps(data), "then": "download"})
        self.assertIn("download=1", r.headers["Location"])
        self.assertEqual(db.session.get(ResumeBuilderData, item.id).title, "Renamed")

    def test_builder_requires_name(self):
        self.register()
        r = self.client.post("/resume/builder/save", data={"title": "x", "template": "modern", "data": "{}"},
                             follow_redirects=True)
        self.assertIn(b"Full name is required", r.data)
        self.assertEqual(ResumeBuilderData.query.count(), 0)


class JobTests(BaseCase):
    def test_search_filters_and_scores(self):
        self.register()
        self.client.post("/profile/", data={"full_name": "Priya Sharma", "skills": "Python, Flask, SQL, Git, REST APIs",
                                            "experience_level": "Fresher", "preferred_locations": "Pune"})
        r = self.client.get("/jobs/?title=python")
        self.assertIn(b"Junior Python Developer", r.data)
        self.assertNotIn(b"Android Developer", r.data)
        self.assertIn(b"Demonstration data", r.data)
        self.assertIn(b"100%", r.data)  # Junior Python Developer: all skills, Fresher, Pune
        r = self.client.get("/jobs/?location=Remote&job_type=Internship")
        self.assertIn(b"Python Backend Intern", r.data)
        self.assertNotIn(b"Junior Python Developer", r.data)
        r = self.client.get("/jobs/?skills=Tableau")
        self.assertIn(b"Business Intelligence Analyst", r.data)

    def test_save_and_unsave(self):
        self.register()
        self.client.post("/jobs/1/save", data={"next": "/jobs/"})
        self.assertEqual(SavedJob.query.count(), 1)
        self.assertIn(b"Junior Python Developer", self.client.get("/jobs/saved").data)
        self.client.post("/jobs/1/save", data={"next": "https://evil.example.com"})
        self.assertEqual(SavedJob.query.count(), 0)


class InterviewTests(BaseCase):
    def test_full_session(self):
        self.register()
        r = self.client.post("/interview/start", data={"domain": "Python", "difficulty": "Beginner", "count": 3, "mode": "bank"},
                             follow_redirects=True)
        self.assertIn(b"Question 1", r.data)
        r = self.client.post("/interview/answer", data={"action": "submit", "answer":
                             "A list is mutable and can be changed, while a tuple is immutable. Lists use square brackets "
                             "and tuples use parentheses; tuples can be dictionary keys."}, follow_redirects=True)
        self.assertIn(b"Suggested answer", r.data)
        p = InterviewProgress.query.one()
        self.assertIsNotNone(p.score)
        self.assertEqual(p.method, "rule")
        self.client.post("/interview/next")
        self.client.post("/interview/answer", data={"action": "skip"})
        self.client.post("/interview/next")
        self.client.post("/interview/answer", data={"action": "submit", "answer": "no idea really"})
        r = self.client.post("/interview/next", follow_redirects=True)
        self.assertIn(b"Session complete", r.data)
        self.assertEqual(InterviewProgress.query.count(), 3)
        self.assertEqual(InterviewProgress.query.filter_by(skipped=True).count(), 1)
        self.assertIn(b"Practice history", self.client.get("/interview/history").data)

    def test_empty_answer_rejected_and_hr(self):
        self.register()
        self.client.post("/interview/start", data={"domain": "HR", "difficulty": "Advanced", "count": 5, "mode": "ai"})
        r = self.client.post("/interview/answer", data={"action": "submit", "answer": ""}, follow_redirects=True)
        self.assertIn(b"Please write an answer", r.data)
        self.assertEqual(InterviewProgress.query.count(), 0)

    def test_invalid_setup(self):
        self.register()
        r = self.client.post("/interview/start", data={"domain": "Cooking", "difficulty": "Beginner", "count": 3},
                             follow_redirects=True)
        self.assertIn(b"valid domain", r.data)


class PageTests(BaseCase):
    def test_all_pages_render(self):
        self.assertEqual(self.client.get("/").status_code, 200)
        self.assertEqual(self.client.get("/login").status_code, 200)
        self.assertEqual(self.client.get("/register").status_code, 200)
        self.register()
        self.upload(sample_docx_bytes(), "priya.docx")
        pages = ["/dashboard", "/resume/analyzer", "/resume/builder", "/resume/builder/new", "/jobs/", "/jobs/saved",
                 "/interview/", "/interview/history", "/profile/"]
        for url in pages:
            r = self.client.get(url)
            self.assertEqual(r.status_code, 200, url)
        self.assertEqual(self.client.get("/does-not-exist").status_code, 404)
        dash = self.client.get("/dashboard").data.decode()
        self.assertIn("categoryChart", dash)
        self.assertTrue(re.search(r"Resumes uploaded</p><p class=\"stat-value\">1<", dash))

    def test_profile_update(self):
        self.register()
        r = self.client.post("/profile/", data={"full_name": "Priya S", "skills": "python, Python, SQL",
                                                "experience_level": "Fresher"}, follow_redirects=True)
        self.assertIn(b"Profile updated", r.data)
        user = User.query.one()
        self.assertEqual(user.profile.skills, "python, SQL")
        r = self.client.post("/profile/", data={"full_name": "Priya", "experience_level": "Wizard"}, follow_redirects=True)
        self.assertIn(b"valid experience level", r.data)


class AIFallbackTests(BaseCase):
    def test_ai_failure_falls_back_to_rules(self):
        self.app.config["AI_API_KEY"] = "invalid-test-key"
        from unittest import mock

        from app.services import ai_service
        with mock.patch.object(ai_service.AIService, "_call", side_effect=ai_service.AIError("Could not reach the AI service.")):
            self.register()
            r = self.upload(sample_docx_bytes(), "priya.docx")
        a = ResumeAnalysis.query.one()
        self.assertEqual(a.method, "rule")
        self.assertIn("rule-based", a.result["ai"]["error"])
        self.assertIn(b"Could not reach the AI service", r.data)

    def test_ai_success_is_labelled(self):
        self.app.config["AI_API_KEY"] = "test-key"
        from unittest import mock

        from app.services import ai_service
        fake = ('{"summary": "Solid fresher resume.", "strengths": ["Clear projects"], "weaknesses": ["No tests"],'
                ' "suggestions": ["Add unit tests"], "recommended_skills": ["Docker", 42, {"bad": 1}]}')
        with mock.patch.object(ai_service.AIService, "_call", return_value=fake):
            self.register()
            r = self.upload(sample_docx_bytes(), "priya.docx")
        a = ResumeAnalysis.query.one()
        self.assertEqual(a.method, "ai")
        self.assertEqual(a.result["ai"]["recommended_skills"], ["Docker", "42"])
        self.assertIn(b"AI-generated feedback", r.data)


if __name__ == "__main__":
    unittest.main()
