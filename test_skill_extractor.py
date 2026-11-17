
from app.services.skill_extractor import extract_skills

sample_resume = """
Python Developer
Skills: Python, Flask, SQL, HTML, CSS, Git.
Experience with Pandas and NumPy.
"""

skills = extract_skills(sample_resume)

print("===== TECHNICAL SKILLS FOUND =====")

if skills:
    for skill in skills:
        print("-", skill)
else:
    print("No recognized skills found.")

print("\nTotal skills found:", len(skills))
