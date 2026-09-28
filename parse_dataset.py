"""
Parser script to convert nlp_job_matching_dataset_verified_job_profiles (1).md
into data/jobs.csv and seed database with 26 verified LinkedIn listings.
"""

import csv
import re
from pathlib import Path

MD_PATH = Path("nlp_job_matching_dataset_verified_job_profiles (1).md")
CSV_PATH = Path("data/jobs.csv")

def parse_markdown_dataset():
    if not MD_PATH.exists():
        raise FileNotFoundError(f"{MD_PATH} not found.")

    with open(MD_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    # Split by job headers ### 1. ...
    job_blocks = re.split(r'\n(?=### \d+\. )', content)
    jobs = []

    for block in job_blocks:
        if not block.strip().startswith("### "):
            continue

        job_data = {
            "job_id": "",
            "title": "",
            "company": "",
            "location": "India",
            "work_mode": "Not specified",
            "job_type": "Full-time",
            "experience": "Not specified",
            "education": "Degree in Computer Science or related field",
            "skills": "",
            "preferred_skills": "",
            "responsibilities": "",
            "description": "",
            "keywords": "",
            "salary": "Competitive Market Standard",
            "source": "LinkedIn Verified",
            "url": ""
        }

        # Parse fields from block
        for line in block.split("\n"):
            line_str = line.strip()

            if line_str.startswith("* **Job ID:**"):
                job_data["job_id"] = re.sub(r'[*`]', '', line_str.split(":", 1)[1]).strip()

            elif line_str.startswith("* **Job Title:**"):
                job_data["title"] = re.sub(r'[*`]', '', line_str.split(":", 1)[1]).strip()

            elif line_str.startswith("* **Company:**"):
                job_data["company"] = re.sub(r'[*`]', '', line_str.split(":", 1)[1]).strip()

            elif line_str.startswith("* **Location:**"):
                job_data["location"] = re.sub(r'[*`]', '', line_str.split(":", 1)[1]).strip()

            elif line_str.startswith("* **Work Mode:**"):
                job_data["work_mode"] = re.sub(r'[*`]', '', line_str.split(":", 1)[1]).strip()

            elif line_str.startswith("* **Employment Type:**"):
                job_data["job_type"] = re.sub(r'[*`]', '', line_str.split(":", 1)[1]).strip()

            elif line_str.startswith("* **Experience Required:**"):
                job_data["experience"] = re.sub(r'[*`]', '', line_str.split(":", 1)[1]).strip()

            elif line_str.startswith("* **Education Required:**"):
                job_data["education"] = re.sub(r'[*`]', '', line_str.split(":", 1)[1]).strip()

            elif line_str.startswith("* **Required Technical Skills:**"):
                job_data["skills"] = re.sub(r'[*`]', '', line_str.split(":", 1)[1]).strip()

            elif line_str.startswith("* **Preferred Skills:**"):
                job_data["preferred_skills"] = re.sub(r'[*`]', '', line_str.split(":", 1)[1]).strip()

            elif line_str.startswith("* **Key Responsibilities:**"):
                job_data["responsibilities"] = re.sub(r'[*`]', '', line_str.split(":", 1)[1]).strip()

            elif line_str.startswith("* **Short Job Description:**"):
                job_data["description"] = re.sub(r'[*`]', '', line_str.split(":", 1)[1]).strip()

            elif line_str.startswith("* **Important NLP Keywords:**"):
                job_data["keywords"] = re.sub(r'[*`]', '', line_str.split(":", 1)[1]).strip()

            elif line_str.startswith("* **LinkedIn Apply URL:**"):
                job_data["url"] = re.sub(r'[*`]', '', line_str.split(":", 1)[1]).strip()

        if job_data["title"] and job_data["url"]:
            jobs.append(job_data)

    print(f"Parsed {len(jobs)} verified job records from dataset.")

    fieldnames = [
        "job_id", "title", "company", "location", "work_mode", "job_type",
        "experience", "education", "skills", "preferred_skills", "responsibilities",
        "description", "keywords", "salary", "source", "url"
    ]

    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for j in jobs:
            writer.writerow(j)

    print(f"Successfully saved {len(jobs)} jobs to {CSV_PATH}.")
    return jobs

if __name__ == "__main__":
    parse_markdown_dataset()
