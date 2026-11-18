"""Skill dictionary, section headings and configurable role/company requirements.

Edit this file to add skills, roles or companies. The company profiles below are
SAMPLE requirement profiles for practice. They are not official hiring criteria.
"""

# Canonical skill name -> extra spellings to search for (case-insensitive, whole word).
# If the list is empty, the canonical name itself is searched.
SKILLS = {
    "Python": [], "Java": [], "C++": ["cpp"], "C#": [], "JavaScript": ["javascript", "js"],
    "TypeScript": [], "PHP": [], "Kotlin": [], "HTML": ["html", "html5"], "CSS": ["css", "css3"],
    "SQL": [], "MySQL": [], "PostgreSQL": ["postgresql", "postgres"], "MongoDB": [], "SQLite": [],
    "Flask": [], "Django": [], "FastAPI": [], "Spring Boot": ["spring boot", "springboot"],
    "Hibernate": [], "Node.js": ["node.js", "nodejs", "node js"], "Express.js": ["express.js", "expressjs"],
    "React": ["react", "reactjs", "react.js"], "Angular": [], "Vue.js": ["vue", "vuejs", "vue.js"],
    "Bootstrap": [], "Tailwind CSS": ["tailwind"], "REST APIs": ["rest api", "rest apis", "restful", "api development"],
    "Git": [], "GitHub": [], "Docker": [], "Kubernetes": [], "AWS": ["aws", "amazon web services"],
    "Azure": [], "Google Cloud": ["google cloud", "gcp"], "Linux": [], "CI/CD": ["ci/cd", "jenkins", "github actions"],
    "Data Structures": ["data structures", "data structure", "dsa"], "Algorithms": ["algorithms", "algorithm"],
    "OOP": ["oop", "oops", "object oriented", "object-oriented"], "DBMS": [], "Operating Systems": [],
    "Computer Networks": ["computer networks", "networking"],
    "Machine Learning": ["machine learning", "ml"], "Deep Learning": [], "NLP": ["nlp", "natural language processing"],
    "Computer Vision": ["computer vision", "opencv"], "TensorFlow": [], "PyTorch": [], "Keras": [],
    "Scikit-learn": ["scikit-learn", "sklearn", "scikit learn"], "Pandas": [], "NumPy": [], "Matplotlib": [],
    "Seaborn": [], "Power BI": ["power bi", "powerbi"], "Tableau": [], "Excel": ["ms excel", "microsoft excel", "advanced excel"],
    "Statistics": [], "Data Analysis": ["data analysis", "data analytics"], "Data Visualization": [],
    "Unit Testing": ["unit testing", "pytest", "unittest", "junit"], "Selenium": [], "Manual Testing": [],
    "Agile": ["agile", "scrum"], "Jira": [], "Android": [], "Flutter": [], "Firebase": [],
    "Cyber Security": ["cyber security", "cybersecurity"],
    "Communication": ["communication"], "Problem Solving": ["problem solving", "problem-solving"],
    "Teamwork": ["teamwork", "team work"], "Leadership": [],
}

# Plain "C" is matched case-sensitively in the parser (to avoid matching every letter c).
SPECIAL_C_LANGUAGE = "C"

SECTION_HEADINGS = {
    "summary": ["summary", "professional summary", "objective", "career objective", "profile", "about me"],
    "education": ["education", "academic details", "academics", "educational qualification",
                  "educational qualifications", "qualifications", "academic qualification"],
    "skills": ["skills", "technical skills", "key skills", "core competencies", "technologies",
               "tech stack", "skill set", "skills summary"],
    "projects": ["projects", "academic projects", "personal projects", "key projects", "project work"],
    "experience": ["experience", "work experience", "professional experience", "internship", "internships",
                   "employment", "work history", "internship experience"],
    "certifications": ["certifications", "certification", "certificates", "courses", "licenses"],
    "achievements": ["achievements", "accomplishments", "awards", "honors", "honours",
                     "extracurricular activities", "positions of responsibility", "activities"],
}

SECTION_LABELS = {
    "summary": "Summary / Objective", "education": "Education", "skills": "Technical Skills",
    "projects": "Projects", "experience": "Work Experience / Internships",
    "certifications": "Certifications", "achievements": "Achievements",
}

# Role -> core skills expected for an entry-level candidate (sample profiles).
ROLE_SKILLS = {
    "Python Developer": ["Python", "Flask", "Django", "SQL", "REST APIs", "Git", "Data Structures", "OOP", "Unit Testing", "Linux"],
    "Java Developer": ["Java", "Spring Boot", "Hibernate", "SQL", "REST APIs", "Git", "Data Structures", "OOP", "Unit Testing"],
    "Full Stack Developer": ["HTML", "CSS", "JavaScript", "React", "Node.js", "SQL", "MongoDB", "REST APIs", "Git"],
    "Frontend Developer": ["HTML", "CSS", "JavaScript", "TypeScript", "React", "Bootstrap", "Git", "REST APIs"],
    "Data Analyst": ["SQL", "Excel", "Python", "Pandas", "Power BI", "Tableau", "Statistics", "Data Visualization"],
    "Data Scientist": ["Python", "Machine Learning", "Pandas", "NumPy", "Scikit-learn", "Statistics", "SQL", "Deep Learning", "Data Visualization"],
    "Machine Learning Engineer": ["Python", "Machine Learning", "Deep Learning", "TensorFlow", "PyTorch", "NumPy", "Scikit-learn", "Git", "Docker"],
    "Software Tester (QA)": ["Manual Testing", "Selenium", "Java", "SQL", "Unit Testing", "Agile", "Jira"],
    "Cloud / DevOps Engineer": ["Linux", "AWS", "Docker", "Kubernetes", "CI/CD", "Git", "Python"],
    "Software Engineer": ["Data Structures", "Algorithms", "OOP", "DBMS", "Operating Systems", "Computer Networks", "SQL", "Git"],
}

# Company -> extra skills that company's recruitment typically emphasises (sample, editable).
COMPANY_FOCUS = {
    "TCS": ["Communication", "Problem Solving", "DBMS", "SQL"],
    "Infosys": ["Data Structures", "OOP", "DBMS", "Communication"],
    "Wipro": ["Communication", "Problem Solving", "Operating Systems", "Computer Networks"],
    "Accenture": ["Communication", "Agile", "Problem Solving", "Azure"],
    "Cognizant": ["SQL", "OOP", "Communication", "Agile"],
    "Capgemini": ["OOP", "DBMS", "Communication", "Agile"],
    "Google": ["Data Structures", "Algorithms", "Problem Solving", "Operating Systems"],
    "Microsoft": ["Data Structures", "Algorithms", "OOP", "Azure"],
}

DEFAULT_ROLE = "Software Engineer"

EXPERIENCE_LEVELS = ["Fresher", "Junior (1-3 yrs)", "Mid-level (3-5 yrs)", "Senior (5+ yrs)"]
JOB_TYPES = ["Full-time", "Internship", "Part-time", "Contract"]


def requirements_for(role, company=""):
    """Combined requirement list for a role (+ optional company focus), without duplicates."""
    skills = list(ROLE_SKILLS.get(role) or ROLE_SKILLS[DEFAULT_ROLE])
    for s in COMPANY_FOCUS.get(company, []):
        if s not in skills:
            skills.append(s)
    return skills
