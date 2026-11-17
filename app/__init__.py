import os
import json
import re

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash
)

from flask_sqlalchemy import SQLAlchemy

from flask_login import (
    LoginManager,
    login_required,
    current_user
)

from flask_wtf.csrf import CSRFProtect


# --------------------------------------------------
# Initialize Flask application
# --------------------------------------------------

app = Flask(__name__)

# Secret key
app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY",
    "dev-key-change-before-deployment"
)

# CSRF protection
csrf = CSRFProtect(app)

# Create instance folder
os.makedirs(app.instance_path, exist_ok=True)


# --------------------------------------------------
# Database configuration
# Local: SQLite
# Render: PostgreSQL
# --------------------------------------------------

DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL:

    if DATABASE_URL.startswith("postgres://"):

        DATABASE_URL = DATABASE_URL.replace(
            "postgres://",
            "postgresql+psycopg://",
            1
        )

    elif DATABASE_URL.startswith("postgresql://"):

        DATABASE_URL = DATABASE_URL.replace(
            "postgresql://",
            "postgresql+psycopg://",
            1
        )

    app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL

else:

    app.config["SQLALCHEMY_DATABASE_URI"] = (
        "sqlite:///"
        + os.path.join(app.instance_path, "resumeai.db")
    )


app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Session cookie security
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

app.config["SESSION_COOKIE_SECURE"] = (
    os.environ.get("RENDER") == "true"
)

# Initialize database
db = SQLAlchemy(app)


# --------------------------------------------------
# Login manager
# --------------------------------------------------

login_manager = LoginManager(app)

login_manager.login_view = "auth.login"


@login_manager.user_loader
def load_user(user_id):

    from app.models.user import User

    return db.session.get(User, int(user_id))


# --------------------------------------------------
# Import models
# --------------------------------------------------

from app.models.user import User


# --------------------------------------------------
# Home page
# --------------------------------------------------

@app.route("/")
def home():

    return render_template("index.html")


# --------------------------------------------------
# Register authentication routes
# --------------------------------------------------

from app.routes.auth import auth

app.register_blueprint(auth)


# --------------------------------------------------
# Register resume analysis routes
# --------------------------------------------------

from app.routes.resume import resume

app.register_blueprint(resume)


# --------------------------------------------------
# Load job roles from project root
# --------------------------------------------------

def load_job_roles():

    roles_path = os.path.join(
        os.path.dirname(app.root_path),
        "job_roles.json"
    )

    try:

        with open(
            roles_path,
            "r",
            encoding="utf-8"
        ) as file:

            roles = json.load(file)

        if not isinstance(roles, dict):

            raise ValueError(
                "job_roles.json must contain a JSON object."
            )

        return roles

    except (
        FileNotFoundError,
        json.JSONDecodeError,
        ValueError
    ) as error:

        app.logger.error(
            "Could not load job_roles.json: %s",
            error
        )

        return {}


# --------------------------------------------------
# Main Dashboard
# --------------------------------------------------

@app.route("/dashboard", methods=["GET", "POST"])
@login_required
def dashboard():

    job_roles = load_job_roles()

    role_names = list(job_roles.keys())

    target_role = getattr(
        current_user,
        "target_role",
        ""
    ) or ""

    if request.method == "POST":

        selected_role = request.form.get(
            "target_role",
            ""
        ).strip()

        if selected_role not in role_names:

            flash(
                "Please select a valid job role.",
                "error"
            )

        else:

            current_user.target_role = selected_role

            db.session.commit()

            flash(
                "Career goal saved successfully!",
                "success"
            )

        return redirect(url_for("dashboard"))

    return render_template(
        "dashboard.html",
        job_roles=role_names,
        target_role=target_role,
        recent_analyses=[]
    )


# --------------------------------------------------
# Job Matching
# --------------------------------------------------

@app.route("/job-matching", methods=["GET", "POST"])
@login_required
def job_matching():

    job_roles = load_job_roles()

    role_names = list(job_roles.keys())

    saved_role = getattr(
        current_user,
        "target_role",
        ""
    ) or ""

    filters = {
        "role": saved_role,
        "location": "",
        "min_salary": "",
        "max_salary": "",
        "experience": "",
        "work_mode": ""
    }

    jobs = []

    searched = False

    message = None

    resume_skills = current_user.resume_skills or []

    if not resume_skills:

        flash(
            "Please upload and analyze your resume first.",
            "error"
        )

        return redirect(url_for("resume.analyze"))

    # Process user preferences

    if request.method == "POST":

        searched = True

        filters = {
            "role": request.form.get("role", "").strip(),
            "location": request.form.get("location", "").strip(),
            "min_salary": request.form.get("min_salary", "").strip(),
            "max_salary": request.form.get("max_salary", "").strip(),
            "experience": request.form.get("experience", "").strip(),
            "work_mode": request.form.get("work_mode", "").strip()
        }

        if filters["role"] not in role_names:

            message = "Please select a valid job role."

        elif not filters["location"]:

            message = "Please enter your preferred location."

        else:

            try:

                min_salary = float(
                    filters["min_salary"] or 0
                )

                max_salary = float(
                    filters["max_salary"] or 0
                )

                if min_salary < 0 or max_salary < 0:
                    raise ValueError

                if max_salary and min_salary > max_salary:
                    raise ValueError

            except ValueError:

                message = "Please enter a valid salary range."

            else:

                jobs_path = os.path.join(
                    os.path.dirname(app.root_path),
                    "jobs.json"
                )

                try:

                    with open(
                        jobs_path,
                        "r",
                        encoding="utf-8"
                    ) as file:

                        all_jobs = json.load(file)

                    if not isinstance(all_jobs, dict):

                        raise ValueError(
                            "jobs.json must contain a JSON object."
                        )

                    role_jobs = all_jobs.get(
                        filters["role"],
                        []
                    )

                    if not isinstance(role_jobs, list):

                        raise ValueError(
                            "Invalid job listings format."
                        )

                    resume_skill_set = {
                        skill.strip().lower()
                        for skill in resume_skills
                        if isinstance(skill, str)
                    }

                    for job in role_jobs:

                        if not isinstance(job, dict):
                            continue

                        # Location matching

                        job_location = job.get(
                            "location",
                            ""
                        )

                        if (
                            filters["location"].lower()
                            not in job_location.lower()
                        ):
                            continue

                        # Salary matching

                        salary_text = job.get("salary", "")

                        job_min = job.get("salary_min_lpa")
                        job_max = job.get("salary_max_lpa")

                        if (
                            job_min is not None
                            and job_max is not None
                        ):

                            job_min = float(job_min)
                            job_max = float(job_max)

                            if min_salary and job_max < min_salary:
                                continue

                            if max_salary and job_min > max_salary:
                                continue

                        else:

                            salary_numbers = re.findall(
                                r"\d+(?:\.\d+)?",
                                salary_text
                            )

                            if salary_numbers:

                                job_min = float(
                                    salary_numbers[0]
                                )

                                job_max = (
                                    float(salary_numbers[1])
                                    if len(salary_numbers) > 1
                                    else job_min
                                )

                                if min_salary and job_max < min_salary:
                                    continue

                                if max_salary and job_min > max_salary:
                                    continue

                        # Experience matching

                        job_experience = job.get(
                            "experience",
                            ""
                        )

                        experience_known = (
                            job_experience
                            and job_experience.lower() not in [
                                "not provided",
                                "not provided in spreadsheet"
                            ]
                        )

                        if (
                            filters["experience"]
                            and experience_known
                            and filters["experience"].lower()
                            not in job_experience.lower()
                        ):
                            continue

                        # Work mode matching

                        job_work_mode = job.get(
                            "work_mode",
                            ""
                        )

                        if (
                            filters["work_mode"]
                            and job_work_mode
                            and filters["work_mode"].lower()
                            != job_work_mode.lower()
                        ):
                            continue

                        # Required skills

                        required_skills = job.get(
                            "required_skills",
                            []
                        )

                        if not isinstance(required_skills, list):
                            required_skills = []

                        # Matching skills

                        matched_skills = [
                            skill
                            for skill in required_skills
                            if isinstance(skill, str)
                            and skill.strip().lower() in resume_skill_set
                        ]

                        # Missing skills

                        missing_skills = [
                            skill
                            for skill in required_skills
                            if isinstance(skill, str)
                            and skill.strip().lower() not in resume_skill_set
                        ]

                        # Match percentage

                        match_percentage = (
                            round(
                                len(matched_skills)
                                / len(required_skills)
                                * 100
                            )
                            if required_skills
                            else 0
                        )

                        jobs.append({

                            "company": job.get(
                                "company",
                                "Not provided"
                            ),

                            "title": job.get(
                                "title",
                                "Not provided"
                            ),

                            "location": job_location,

                            "salary": (
                                salary_text or "Not disclosed"
                            ),

                            "experience": (
                                job_experience
                                if experience_known
                                else "Not provided"
                            ),

                            "work_mode": (
                                job_work_mode or "Not provided"
                            ),

                            "required_skills": required_skills,

                            "matched_skills": matched_skills,

                            "missing_skills": missing_skills,

                            "match_percentage": match_percentage

                        })

                    # Sort by resume match percentage

                    jobs.sort(
                        key=lambda job: job["match_percentage"],
                        reverse=True
                    )

                    if not jobs:

                        message = (
                            "No matching jobs found. "
                            "Try changing your preferences."
                        )

                    current_user.target_role = filters["role"]

                    db.session.commit()

                except FileNotFoundError:

                    app.logger.exception(
                        "jobs.json file not found."
                    )

                    message = "Job listings file was not found."

                except (
                    json.JSONDecodeError,
                    ValueError,
                    TypeError
                ):

                    app.logger.exception(
                        "Could not process jobs.json."
                    )

                    message = (
                        "There was a problem reading job listings."
                    )

    return render_template(
        "job_matching.html",
        job_roles=role_names,
        target_role=filters["role"],
        filters=filters,
        jobs=jobs,
        searched=searched,
        message=message,
        api_error=None
    )


# --------------------------------------------------
# Learning and Skill Development
# --------------------------------------------------

@app.route("/learning")
@login_required
def learning():

    job_roles = load_job_roles()

    role_names = list(job_roles.keys())

    selected_role = request.args.get(
        "role",
        ""
    ).strip()

    if selected_role:

        if selected_role in role_names:
            target_role = selected_role
        else:
            target_role = ""

    else:

        target_role = current_user.target_role or ""

    resources_path = os.path.join(
        os.path.dirname(app.root_path),
        "learning_resources.json"
    )

    resources = []

    resume_skills = current_user.resume_skills or []

    if not isinstance(resume_skills, list):
        resume_skills = []

    required_skills = job_roles.get(
        target_role,
        []
    )

    if not isinstance(required_skills, list):
        required_skills = []

    resume_skill_set = {
        skill.strip().casefold()
        for skill in resume_skills
        if isinstance(skill, str)
    }

    matched_skills = [
        skill
        for skill in required_skills
        if isinstance(skill, str)
        and skill.strip().casefold() in resume_skill_set
    ]

    missing_skills = [
        skill
        for skill in required_skills
        if isinstance(skill, str)
        and skill.strip().casefold() not in resume_skill_set
    ]

    try:

        with open(
            resources_path,
            "r",
            encoding="utf-8"
        ) as file:

            learning_data = json.load(file)

        if not isinstance(learning_data, dict):

            raise ValueError(
                "learning_resources.json must contain a JSON object."
            )

        resources = learning_data.get(
            target_role,
            []
        )

        if not isinstance(resources, list):

            resources = []

        else:

            resources = [
                resource
                for resource in resources
                if isinstance(resource, dict)
            ]

            for resource in resources:

                resource_text = " ".join(
                    str(resource.get(field, ""))
                    for field in ("topic", "title")
                ).casefold()

                resource["focus_skills"] = [
                    skill
                    for skill in missing_skills
                    if skill.casefold() in resource_text
                ]

            resources.sort(
                key=lambda resource: not resource["focus_skills"]
            )

    except FileNotFoundError:

        app.logger.error(
            "learning_resources.json not found."
        )

    except (
        json.JSONDecodeError,
        ValueError
    ):

        app.logger.exception(
            "Could not process learning_resources.json."
        )

    return render_template(
        "learning.html",
        job_roles=job_roles,
        target_role=target_role,
        resources=resources,
        required_skills=required_skills,
        matched_skills=matched_skills,
        missing_skills=missing_skills,
        resume_skills=resume_skills
    )


# --------------------------------------------------
# Interview and Career Readiness
# --------------------------------------------------

@app.route("/career-readiness")
@login_required
def career_readiness():

    resources_path = os.path.join(
        os.path.dirname(app.root_path),
        "interview_resources.json"
    )

    interview_data = {
        "technical_interview": [],
        "hr_interview": [],
        "communication_skills": []
    }

    try:

        with open(
            resources_path,
            "r",
            encoding="utf-8"
        ) as file:

            loaded_data = json.load(file)

        if not isinstance(loaded_data, dict):

            raise ValueError(
                "interview_resources.json must contain a JSON object."
            )

        for category in interview_data:

            category_resources = loaded_data.get(
                category,
                []
            )

            if isinstance(category_resources, list):

                interview_data[category] = [
                    resource
                    for resource in category_resources
                    if isinstance(resource, dict)
                    and resource.get("url")
                    and resource.get("title")
                ]

            else:

                interview_data[category] = []

    except FileNotFoundError:

        app.logger.error(
            "interview_resources.json not found."
        )

    except (
        json.JSONDecodeError,
        ValueError
    ):

        app.logger.exception(
            "Could not process interview_resources.json."
        )

    return render_template(
        "career_readiness.html",
        interview_data=interview_data
    )