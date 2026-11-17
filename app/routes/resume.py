import os
import uuid
import io
import json
import zipfile

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    current_app,
)

from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from app import db
from app.services.resume_parser import extract_resume_text
from app.services.skill_extractor import extract_skills


resume = Blueprint("resume", __name__, url_prefix="/resume")

ALLOWED_EXTENSIONS = {"pdf", "docx"}
MAX_FILE_SIZE = 10 * 1024 * 1024


def load_job_roles():
    """Load job roles and their required skills from job_roles.json."""

    project_folder = os.path.abspath(
        os.path.join(current_app.root_path, "..")
    )

    roles_file = os.path.join(project_folder, "job_roles.json")

    with open(roles_file, "r", encoding="utf-8") as file:
        roles = json.load(file)

    if not isinstance(roles, dict) or not roles:
        raise ValueError("Invalid or empty job_roles.json")

    return roles


@resume.route("/", methods=["GET", "POST"])
@login_required
def analyze():

    try:
        job_roles = load_job_roles()

    except (OSError, json.JSONDecodeError, ValueError):
        current_app.logger.exception(
            "Could not load job_roles.json"
        )

        flash(
            "Could not load job roles. Please check job_roles.json.",
            "error"
        )

        return redirect(url_for("home"))

    if request.method == "POST":

        uploaded_file = request.files.get("resume_file")

        job_role = request.form.get(
            "job_role", ""
        ).strip()

        # Validate uploaded resume.

        if not uploaded_file or not uploaded_file.filename:
            flash("Please upload your resume.", "error")
            return redirect(url_for("resume.analyze"))

        # Validate selected job role.

        if job_role not in job_roles:
            flash("Please select a valid job role.", "error")
            return redirect(url_for("resume.analyze"))

        original_filename = secure_filename(
            uploaded_file.filename
        )

        if (
            not original_filename
            or "." not in original_filename
            or original_filename.rsplit(".", 1)[1].lower()
            not in ALLOWED_EXTENSIONS
        ):
            flash(
                "Please upload a PDF or DOCX file.",
                "error"
            )

            return redirect(url_for("resume.analyze"))

        extension = original_filename.rsplit(
            ".", 1
        )[1].lower()

        file_data = uploaded_file.read()

        if not file_data:
            flash(
                "The uploaded file is empty.",
                "error"
            )

            return redirect(url_for("resume.analyze"))

        if len(file_data) > MAX_FILE_SIZE:
            flash(
                "The resume must be 10 MB or smaller.",
                "error"
            )

            return redirect(url_for("resume.analyze"))

        # Validate PDF file.

        if extension == "pdf" and not file_data.startswith(b"%PDF-"):

            flash(
                "The file does not appear to be a valid PDF.",
                "error"
            )

            return redirect(url_for("resume.analyze"))

        # Validate DOCX file.

        if extension == "docx":

            try:
                with zipfile.ZipFile(
                    io.BytesIO(file_data)
                ) as docx:

                    names = docx.namelist()

                    if (
                        "[Content_Types].xml" not in names
                        or "word/document.xml" not in names
                    ):
                        raise ValueError("Invalid DOCX")

            except (zipfile.BadZipFile, ValueError):

                flash(
                    "The file does not appear to be a valid DOCX.",
                    "error"
                )

                return redirect(url_for("resume.analyze"))

        # Create upload folder.

        stored_filename = (
            f"{uuid.uuid4().hex}.{extension}"
        )

        upload_folder = os.path.abspath(
            os.path.join(
                current_app.root_path,
                "..",
                "uploads"
            )
        )

        os.makedirs(
            upload_folder,
            exist_ok=True
        )

        file_path = os.path.join(
            upload_folder,
            stored_filename
        )

        with open(file_path, "wb") as file:
            file.write(file_data)

        try:

            # Extract resume text.

            resume_text = extract_resume_text(
                file_path
            )

            # Extract skills from resume.

            found_skills = extract_skills(
                resume_text
            )

            # Get required skills for selected role.

            required_skills = job_roles[job_role]

            # Compare skills without case sensitivity.

            found_lower = {
                skill.lower()
                for skill in found_skills
            }

            matched_skills = [
                skill
                for skill in required_skills
                if skill.lower() in found_lower
            ]

            missing_skills = [
                skill
                for skill in required_skills
                if skill.lower() not in found_lower
            ]

            # Calculate skill match percentage.

            percentage = (
                round(
                    len(matched_skills)
                    / len(required_skills)
                    * 100,
                    1
                )
                if required_skills
                else 0
            )

            # Save complete resume analysis in database.

            current_user.target_role = job_role

            current_user.resume_skills = found_skills

            current_user.matched_skills = matched_skills

            current_user.missing_skills = missing_skills

            db.session.commit()

        except Exception as error:

            db.session.rollback()

            current_app.logger.exception(
                "Resume analysis or database saving failed"
            )

            if "No readable text found" in str(error):

                flash(
                    "No readable text was found. This may be a scanned "
                    "resume that requires OCR.",
                    "error"
                )

            else:

                flash(
                    "Could not analyze this resume. Please try another "
                    "valid PDF or DOCX file.",
                    "error"
                )

            return redirect(
                url_for("resume.analyze")
            )

        finally:

            # Remove temporary uploaded file.

            try:
                os.remove(file_path)

            except OSError:
                pass

        # Display analysis results.

        return render_template(
            "resume.html",

            found_skills=found_skills,
            matched_skills=matched_skills,
            missing_skills=missing_skills,

            percentage=percentage,
            required_skills=required_skills,

            job_roles=job_roles,
            selected_job_role=job_role,

            analyzed=True
        )

    # Display resume upload page.

    return render_template(
        "resume.html",

        job_roles=job_roles,

        analyzed=False
    )