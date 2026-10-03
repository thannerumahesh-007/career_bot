"""
Tests for AI Mock Interview Simulator Service and API Endpoints.
"""

import unittest
import json
from app import app
from database.database import init_db, SessionLocal, engine
from database.models import User, Base, InterviewSession
from services.interview_service import interview_service


class TestAIInterviewSimulator(unittest.TestCase):

    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()

        Base.metadata.drop_all(bind=engine)
        init_db()

        # Seed authenticated user
        db = SessionLocal()
        user = User(full_name="Grace Hopper", username="gracehopper", email="grace@hopper.io")
        user.set_password("SecurePass123!")
        db.add(user)
        db.commit()
        self.user_id = user.id
        db.close()

        with self.client.session_transaction() as sess:
            sess["user_id"] = self.user_id
            sess["username"] = "gracehopper"
            sess["full_name"] = "Grace Hopper"

    def test_question_generation_produces_5_role_specific_questions(self):
        """Verify interview service creates exactly 5 structured questions."""
        questions = interview_service.generate_interview_questions(
            role="data analyst",
            difficulty="Intermediate",
            interview_type="Technical"
        )
        self.assertEqual(len(questions), 5)
        for idx, q in enumerate(questions):
            self.assertEqual(q["id"], idx + 1)
            self.assertTrue(len(q["question"]) > 10)
            self.assertIn("type", q)

    def test_answer_evaluation_rubric_bounds(self):
        """Verify rubric components are scored within 1-10 bounds."""
        question = {
            "id": 1,
            "type": "technical_core",
            "question": "How do you handle missing values and outliers in Pandas?",
            "focus": "Data cleaning techniques and statistical imputation"
        }
        answer = "I inspect missing data using isnull().sum(), impute with median for skewed distributions, and drop if missing is minimal. For outliers, I use IQR or Z-score."

        eval_result = interview_service.evaluate_interview_answer(
            role="data analyst",
            difficulty="Intermediate",
            question=question,
            answer=answer
        )

        self.assertIn("score", eval_result)
        self.assertIn("rubric", eval_result)
        self.assertIn("feedback", eval_result)
        self.assertTrue(1 <= eval_result["score"] <= 10)

        rubric = eval_result["rubric"]
        for k in ["correctness", "relevance", "completeness", "technical_depth", "communication"]:
            self.assertTrue(1 <= rubric[k] <= 10)

    def test_full_5_question_interview_session_flow(self):
        """Verify complete progression through all 5 questions culminating in final report."""
        # 1. Start session via API
        start_res = self.client.post('/api/interview/start', json={
            "target_role": "Data Analyst",
            "difficulty": "Intermediate",
            "interview_type": "Technical"
        })
        self.assertEqual(start_res.status_code, 200)
        start_data = start_res.get_json()
        session_id = start_data["session_id"]
        self.assertEqual(start_data["status"], "in_progress")
        self.assertEqual(start_data["total_questions"], 5)

        # 2. Answer questions 1 to 4
        answers = [
            "I have experience extracting data via SQL and creating interactive dashboards in Power BI.",
            "SQL Joins combine rows from multiple tables based on related keys, such as Inner Join, Left Join, and Full Outer Join.",
            "I use window functions like ROW_NUMBER() and RANK() partitioned by customer ID to calculate running totals.",
            "In a production ETL pipeline, I log records, validate schema integrity, and send automated Slack alerts on failure."
        ]

        for ans in answers:
            ans_res = self.client.post('/api/interview/answer', json={
                "session_id": session_id,
                "answer": ans
            })
            self.assertEqual(ans_res.status_code, 200)
            data = ans_res.get_json()
            self.assertEqual(data["status"], "in_progress")

        # 3. Answer question 5 (final question)
        final_ans_res = self.client.post('/api/interview/answer', json={
            "session_id": session_id,
            "answer": "When facing a tight deadline on a critical executive report, I prioritized core KPIs first and collaborated closely with the product manager."
        })
        self.assertEqual(final_ans_res.status_code, 200)
        final_data = final_ans_res.get_json()
        self.assertEqual(final_data["status"], "completed")
        self.assertIn("final_report", final_data)

        report = final_data["final_report"]
        self.assertTrue(0 <= report["overall_score"] <= 100)
        self.assertTrue(len(report["strengths"]) > 0)
        self.assertTrue(len(report["recommended_topics"]) > 0)


if __name__ == "__main__":
    unittest.main()
