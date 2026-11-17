
from app.services.resume_parser import extract_resume_text

file_path = input("Enter the full path of your PDF or DOCX resume: ")

try:
    text = extract_resume_text(file_path)

    print("\n===== EXTRACTED RESUME TEXT =====\n")
    print(text)

    print("\n===== EXTRACTION SUCCESSFUL =====")

except Exception as error:
    print(f"\nExtraction failed: {error}")
