"""Resume builder data: default structure and server-side validation of what the browser sends."""
import json

TEMPLATES = {
    "modern": "Modern (navy accents)",
    "classic": "Classic (serif, centered)",
    "compact": "Compact (fits more on one page)",
}

SECTION_ORDER = ["summary", "education", "skills", "projects", "experience",
                 "certifications", "achievements", "languages"]

LIST_FIELDS = {
    "education": ["degree", "institution", "year", "score"],
    "projects": ["title", "tech", "link", "description"],
    "experience": ["role", "company", "duration", "description"],
    "certifications": ["name", "issuer", "year"],
    "achievements": ["text"],
}
PERSONAL_FIELDS = ["full_name", "email", "phone", "location", "linkedin", "github", "website"]


def default_data(user):
    p = user.profile
    return {
        "personal": {"full_name": user.full_name, "email": user.email,
                     "phone": p.phone if p else "", "location": p.location if p else "",
                     "linkedin": "", "github": "", "website": ""},
        "summary": p.headline if p else "",
        "education": [{"degree": "", "institution": "", "year": "", "score": ""}],
        "skills": p.skills if p else "",
        "projects": [{"title": "", "tech": "", "link": "", "description": ""}],
        "experience": [],
        "certifications": [],
        "achievements": [],
        "languages": "English",
        "hidden": [],
    }


def _s(value, limit=2000):
    return str(value).strip()[:limit] if isinstance(value, (str, int, float)) else ""


def clean_data(raw_json):
    """Parse and whitelist builder JSON. Raises ValueError on invalid input."""
    try:
        raw = json.loads(raw_json or "{}")
    except json.JSONDecodeError as e:
        raise ValueError("Resume data could not be read.") from e
    if not isinstance(raw, dict):
        raise ValueError("Resume data could not be read.")

    personal = raw.get("personal") if isinstance(raw.get("personal"), dict) else {}
    data = {"personal": {f: _s(personal.get(f), 200) for f in PERSONAL_FIELDS}}
    data["summary"] = _s(raw.get("summary"), 1500)
    data["skills"] = _s(raw.get("skills"), 1000)
    data["languages"] = _s(raw.get("languages"), 300)
    for key, fields in LIST_FIELDS.items():
        items = raw.get(key) if isinstance(raw.get(key), list) else []
        cleaned = []
        for item in items[:20]:
            if isinstance(item, dict):
                entry = {f: _s(item.get(f)) for f in fields}
                if any(entry.values()):
                    cleaned.append(entry)
        data[key] = cleaned
    hidden = raw.get("hidden") if isinstance(raw.get("hidden"), list) else []
    data["hidden"] = [h for h in hidden if h in SECTION_ORDER]

    if not data["personal"]["full_name"]:
        raise ValueError("Full name is required in Personal Details.")
    return data
