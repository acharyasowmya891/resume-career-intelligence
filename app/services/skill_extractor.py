
import re

# Technical skills only
SKILL_DICTIONARY = [
    "Python",
    "Java",
    "JavaScript",
    "C++",
    "C#",
    "C",
    "SQL",
    "MySQL",
    "SQLite",
    "PostgreSQL",
    "MongoDB",
    "HTML",
    "CSS",
    "Flask",
    "Django",
    "React",
    "Node.js",
    "Git",
    "GitHub",
    "REST API",
    "Docker",
    "AWS",
    "Machine Learning",
    "Deep Learning",
    "TensorFlow",
    "PyTorch",
    "Scikit-learn",
    "Pandas",
    "NumPy",
    "Excel",
    "Power BI",
    "Tableau",
    "Linux",
    
]


def extract_skills(resume_text):
    """Extract technical skills and ignore URLs."""

    if not resume_text:
        return []

    # Remove URLs before searching for skills.
    text = re.sub(
        r"https?://\S+|www\.\S+",
        " ",
        resume_text,
        flags=re.IGNORECASE,
    )

    text = text.lower()
    found_skills = []

    # Match complete skill names only.
    for skill in SKILL_DICTIONARY:
        pattern = (
            r"(?<!\w)"
            + re.escape(skill.lower())
            + r"(?!\w)"
        )

        if re.search(pattern, text):
            found_skills.append(skill)

    return found_skills
