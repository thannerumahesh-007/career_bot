"""
AI Mock Interview Simulator Service for CareerBot.
Manages interactive mock interview sessions, generates tailored questions,
evaluates responses using the 5-point rubric, tracks turns, and produces comprehensive final reports.
"""

import json
import logging
import re
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

from database.database import SessionLocal
from database.models import InterviewSession, Resume
from services.model_router import model_router
from services.career_knowledge import get_role_details, extract_role_from_text

logger = logging.getLogger("careerbot.interview")


class InterviewService:
    """Manages AI-driven mock interview simulations with fallback resilience."""

    def __init__(self):
        pass

    def _get_offline_questions(self, role: str, difficulty: str = "Intermediate") -> List[Dict[str, Any]]:
        """Produces 5 structured fallback questions when Gemini is unavailable."""
        role_info = get_role_details(role)
        role_title = role_info.get("title", role.title())
        req_skills = role_info.get("required_skills", ["Problem Solving", "Technical Communication"])
        interview_topics = role_info.get("interview_topics", [
            f"Core {role_title} architecture and methodologies",
            f"Performance optimization and debugging in {role_title}"
        ])

        skill_1 = req_skills[0] if len(req_skills) > 0 else "core programming"
        skill_2 = req_skills[1] if len(req_skills) > 1 else "data structures"
        topic_1 = interview_topics[0] if len(interview_topics) > 0 else f"{role_title} best practices"
        topic_2 = interview_topics[1] if len(interview_topics) > 1 else f"Troubleshooting and system reliability in {role_title}"

        return [
            {
                "id": 1,
                "type": "introductory",
                "question": f"Walk me through your background and how your hands-on experience prepares you for a {role_title} role at the {difficulty} level.",
                "focus": "Communication, professional trajectory, alignment with role"
            },
            {
                "id": 2,
                "type": "technical_core",
                "question": f"In {role_title}, how would you explain the core concepts of {skill_1}, and what are the key trade-offs to keep in mind when implementing it?",
                "focus": f"Depth of understanding in {skill_1}"
            },
            {
                "id": 3,
                "type": "technical_deep",
                "question": f"Let's discuss {topic_1}. How do you approach this in production environments, particularly regarding {skill_2}?",
                "focus": f"Architecture, best practices, and real-world application of {skill_2}"
            },
            {
                "id": 4,
                "type": "scenario",
                "question": f"Scenario: Suppose you are tasked with resolving: {topic_2}. Step-by-step, how would you diagnose the root cause and implement a resilient fix?",
                "focus": "Problem-solving methodology, debugging, and analytical thinking"
            },
            {
                "id": 5,
                "type": "behavioral",
                "question": f"Tell me about a challenging technical hurdle or disagreement you encountered during a project related to {role_title}. How did you resolve it under deadline pressure?",
                "focus": "Collaboration, conflict resolution, resilience under pressure"
            }
        ]

    def generate_interview_questions(
        self,
        role: str,
        difficulty: str = "Intermediate",
        interview_type: str = "Technical",
        resume_context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Generates 5 role-specific interview questions using Gemini Model Router with offline fallback."""
        role_info = get_role_details(role)
        role_title = role_info.get("title", role.title())
        skills_str = ", ".join(role_info.get("required_skills", [])[:5])

        resume_summary = ""
        if resume_context:
            extracted_skills = resume_context.get("skills", [])
            extracted_exp = resume_context.get("experience", "")
            if extracted_skills:
                resume_summary += f"Candidate resume skills: {', '.join(extracted_skills[:8])}. "
            if extracted_exp:
                resume_summary += f"Candidate background: {extracted_exp[:200]}."

        system_instruction = (
            "You are a Senior Principal Technical Interviewer conducting a rigorous, professional mock interview. "
            "You always respond with strictly valid JSON only. No markdown fences, no conversational preamble."
        )

        prompt = (
            f"Generate exactly 5 realistic, high-quality interview questions for a {difficulty} level {role_title} position.\n"
            f"Interview Type: {interview_type}\n"
            f"Target Role Core Skills: {skills_str}\n"
            f"{resume_summary}\n\n"
            "Format the questions into this exact JSON array of 5 objects:\n"
            "[\n"
            "  {\n"
            "    \"id\": 1,\n"
            "    \"type\": \"introductory\",\n"
            "    \"question\": \"Question text here\",\n"
            "    \"focus\": \"Evaluation criteria\"\n"
            "  },\n"
            "  {\n"
            "    \"id\": 2,\n"
            "    \"type\": \"technical_core\",\n"
            "    \"question\": \"Core technical question\",\n"
            "    \"focus\": \"Evaluation criteria\"\n"
            "  },\n"
            "  {\n"
            "    \"id\": 3,\n"
            "    \"type\": \"technical_deep\",\n"
            "    \"question\": \"In-depth technical architecture/tool question\",\n"
            "    \"focus\": \"Evaluation criteria\"\n"
            "  },\n"
            "  {\n"
            "    \"id\": 4,\n"
            "    \"type\": \"scenario\",\n"
            "    \"question\": \"Real-world scenario / problem-solving question\",\n"
            "    \"focus\": \"Evaluation criteria\"\n"
            "  },\n"
            "  {\n"
            "    \"id\": 5,\n"
            "    \"type\": \"behavioral\",\n"
            "    \"question\": \"Situational or STAR-method behavioral question\",\n"
            "    \"focus\": \"Evaluation criteria\"\n"
            "  }\n"
            "]"
        )

        try:
            response_text = model_router.generate_content(
                task="interview",
                prompt=prompt,
                system_instruction=system_instruction
            )

            # Clean JSON response
            cleaned_text = response_text.strip()
            if cleaned_text.startswith("```json"):
                cleaned_text = cleaned_text[7:]
            if cleaned_text.startswith("```"):
                cleaned_text = cleaned_text[3:]
            if cleaned_text.endswith("```"):
                cleaned_text = cleaned_text[:-3]
            cleaned_text = cleaned_text.strip()

            parsed = json.loads(cleaned_text)
            if isinstance(parsed, list) and len(parsed) == 5:
                # Sanitize IDs and fields
                for idx, q in enumerate(parsed):
                    q["id"] = idx + 1
                return parsed
        except Exception as e:
            logger.warning(f"Gemini question generation fallback triggered: {e}")

        return self._get_offline_questions(role, difficulty)

    def evaluate_interview_answer(
        self,
        role: str,
        difficulty: str,
        question: Dict[str, Any],
        answer: str
    ) -> Dict[str, Any]:
        """Evaluates an answer against the 5-criterion rubric with feedback and score."""
        if not answer or len(answer.strip()) < 5:
            return {
                "score": 1,
                "rubric": {
                    "correctness": 1,
                    "relevance": 1,
                    "completeness": 1,
                    "technical_depth": 1,
                    "communication": 1
                },
                "feedback": "The answer was very brief or empty. Please elaborate with specific technical explanations, architecture choices, or concrete examples.",
                "ideal_points": ["Provide a structured response covering concepts, implementation details, and trade-offs."]
            }

        system_instruction = (
            "You are an expert technical interviewer evaluating a candidate's answer. "
            "Evaluate strictly and constructively. Return valid JSON only without markdown formatting."
        )

        prompt = (
            f"Target Role: {role} ({difficulty})\n"
            f"Question Type: {question.get('type')}\n"
            f"Question: {question.get('question')}\n"
            f"Focus Area: {question.get('focus')}\n\n"
            f"Candidate's Answer:\n\"\"\"{answer}\"\"\"\n\n"
            "Evaluate this answer according to this rubric (scores 1 to 10 each):\n"
            "- correctness: factual technical accuracy\n"
            "- relevance: how directly it addresses the prompt\n"
            "- completeness: covers key considerations and trade-offs\n"
            "- technical_depth: demonstrates mastery of tools, algorithms, or frameworks\n"
            "- communication: clarity, structure, and professional vocabulary\n\n"
            "Return valid JSON in this exact structure:\n"
            "{\n"
            "  \"score\": 7,\n"
            "  \"rubric\": {\n"
            "    \"correctness\": 7,\n"
            "    \"relevance\": 8,\n"
            "    \"completeness\": 6,\n"
            "    \"technical_depth\": 7,\n"
            "    \"communication\": 8\n"
            "  },\n"
            "  \"feedback\": \"Constructive 2-3 sentence review highlighting strengths and gaps.\",\n"
            "  \"ideal_points\": [\"Key point 1\", \"Key point 2\", \"Key point 3\"]\n"
            "}"
        )

        try:
            response_text = model_router.generate_content(
                task="interview",
                prompt=prompt,
                system_instruction=system_instruction
            )

            cleaned_text = response_text.strip()
            if cleaned_text.startswith("```json"):
                cleaned_text = cleaned_text[7:]
            if cleaned_text.startswith("```"):
                cleaned_text = cleaned_text[3:]
            if cleaned_text.endswith("```"):
                cleaned_text = cleaned_text[:-3]
            cleaned_text = cleaned_text.strip()

            parsed = json.loads(cleaned_text)
            if "score" in parsed and "rubric" in parsed:
                # Ensure rubric values are bounded
                rubric = parsed.get("rubric", {})
                for k in ["correctness", "relevance", "completeness", "technical_depth", "communication"]:
                    rubric[k] = max(1, min(10, int(rubric.get(k, 5))))
                avg_score = round(sum(rubric.values()) / len(rubric))
                parsed["score"] = avg_score
                return parsed
        except Exception as e:
            logger.warning(f"Gemini answer evaluation fallback triggered: {e}")

        # Deterministic fallback evaluation based on keyword presence and answer depth
        words = len(answer.split())
        base_depth = min(10, max(3, words // 15))
        role_info = get_role_details(role)
        role_skills = [s.lower() for s in role_info.get("required_skills", [])]
        matched_skills = [s for s in role_skills if any(w in answer.lower() for w in s.split()[:2])]
        skill_boost = min(3, len(matched_skills))

        correctness = min(10, max(4, base_depth + skill_boost - 1))
        relevance = min(10, max(5, base_depth + 1))
        completeness = min(10, max(3, base_depth))
        tech_depth = min(10, max(4, base_depth + skill_boost))
        communication = min(10, max(5, 6 if words >= 25 else 4))
        avg_score = round((correctness + relevance + completeness + tech_depth + communication) / 5)

        return {
            "score": avg_score,
            "rubric": {
                "correctness": correctness,
                "relevance": relevance,
                "completeness": completeness,
                "technical_depth": tech_depth,
                "communication": communication
            },
            "feedback": f"Demonstrated reasonable conceptual grasp with {words} words. To improve, incorporate more concrete production examples and technical keywords ({', '.join(role_skills[:3])}).",
            "ideal_points": [
                f"Clarify architecture and trade-offs in {role_info.get('title', role)}",
                "Use the STAR method (Situation, Task, Action, Result) for scenario questions",
                "Highlight measurement metrics or performance outcomes"
            ]
        }

    def _generate_final_report(self, session: InterviewSession) -> Dict[str, Any]:
        """Calculates final interview score, readiness tier, strengths, and study plan."""
        turns = session.turns
        if not turns:
            return {
                "overall_score": 0,
                "readiness_level": "Incomplete",
                "rubric_averages": {},
                "strengths": ["Interview not completed"],
                "improvements": ["Complete all 5 questions to receive a comprehensive analysis."],
                "recommended_topics": []
            }

        scores = [t.get("evaluation", {}).get("score", 5) for t in turns]
        overall_score = round((sum(scores) / (len(scores) * 10)) * 100)

        # Average rubric components
        rubric_totals = {"correctness": 0, "relevance": 0, "completeness": 0, "technical_depth": 0, "communication": 0}
        for t in turns:
            rub = t.get("evaluation", {}).get("rubric", {})
            for k in rubric_totals:
                rubric_totals[k] += rub.get(k, 5)

        rubric_averages = {k: round(v / len(turns), 1) for k, v in rubric_totals.items()}

        # Readiness classification
        if overall_score >= 85:
            readiness_level = "Exceptional — Ready for Senior/Staff Interviews"
        elif overall_score >= 70:
            readiness_level = "Job Ready — Strong Candidate for Target Role"
        elif overall_score >= 55:
            readiness_level = "Progressing — Solid Foundation with Specific Technical Gaps"
        else:
            readiness_level = "Foundational — Requires Deeper Hands-on Project Practice"

        # Role study recommendations
        role_info = get_role_details(session.target_role)
        rec_topics = role_info.get("interview_topics", [])
        rec_certs = role_info.get("certifications", [])

        strengths = []
        improvements = []

        if rubric_averages.get("communication", 0) >= 7.0:
            strengths.append("Clear articulation and professional communication structure.")
        else:
            improvements.append("Structure answers with clear problem-statement, action taken, and measurable results.")

        if rubric_averages.get("technical_depth", 0) >= 7.0:
            strengths.append(f"Strong command of {role_info.get('title', session.target_role)} technical vocabulary and implementation.")
        else:
            improvements.append(f"Deepen knowledge of core systems, data structures, and trade-offs in {role_info.get('title')}.")

        if rubric_averages.get("correctness", 0) >= 7.0:
            strengths.append("High factual and conceptual accuracy throughout answers.")
        else:
            improvements.append("Verify technical definitions and operational mechanisms before answering.")

        if not strengths:
            strengths.append("Good initiative and participation in full interview flow.")
        if not improvements:
            improvements.append("Maintain consistency across complex system design scenarios.")

        return {
            "overall_score": overall_score,
            "readiness_level": readiness_level,
            "rubric_averages": rubric_averages,
            "strengths": strengths,
            "improvements": improvements,
            "recommended_topics": rec_topics,
            "recommended_certifications": rec_certs,
            "turns_summary": [
                {
                    "question_id": t.get("question_id"),
                    "question": t.get("question"),
                    "score": t.get("evaluation", {}).get("score", 0),
                    "feedback": t.get("evaluation", {}).get("feedback", "")
                }
                for t in turns
            ]
        }

    def start_session(
        self,
        user_id: int,
        target_role: str,
        difficulty: str = "Intermediate",
        interview_type: str = "Technical"
    ) -> Dict[str, Any]:
        """Creates and initializes a new interview session in DB."""
        db = SessionLocal()
        try:
            canonical_role = extract_role_from_text(target_role) or target_role.strip()
            
            # Fetch user resume context if available
            latest_resume = db.query(Resume).filter_by(user_id=user_id).order_by(Resume.uploaded_at.desc()).first()
            resume_context = None
            if latest_resume and latest_resume.extracted_data:
                resume_context = latest_resume.extracted_data

            questions = self.generate_interview_questions(
                role=canonical_role,
                difficulty=difficulty,
                interview_type=interview_type,
                resume_context=resume_context
            )

            session = InterviewSession(
                user_id=user_id,
                target_role=canonical_role,
                interview_type=interview_type,
                difficulty=difficulty,
                status="in_progress",
                current_question_index=0,
                questions_json=json.dumps(questions),
                turns_json="[]",
                final_report_json="{}"
            )
            db.add(session)
            db.commit()
            db.refresh(session)

            first_question = questions[0] if questions else None

            return {
                "success": True,
                "session_id": session.id,
                "target_role": session.target_role,
                "difficulty": session.difficulty,
                "interview_type": session.interview_type,
                "total_questions": len(questions),
                "current_question_index": 0,
                "current_question": first_question,
                "status": "in_progress"
            }
        except Exception as e:
            db.rollback()
            logger.error(f"Error starting interview session: {e}")
            raise
        finally:
            db.close()

    def submit_answer(self, session_id: int, user_id: int, answer: str) -> Dict[str, Any]:
        """Processes candidate answer for current question, updates score, advances or completes."""
        db = SessionLocal()
        try:
            session = db.query(InterviewSession).filter_by(id=session_id, user_id=user_id).first()
            if not session:
                return {"success": False, "error": "Interview session not found or unauthorized"}

            if session.status == "completed":
                return {
                    "success": False,
                    "error": "Interview session has already been completed",
                    "final_report": session.final_report
                }

            questions = session.questions
            curr_idx = session.current_question_index

            if curr_idx >= len(questions):
                session.status = "completed"
                db.commit()
                return {"success": True, "status": "completed", "final_report": session.final_report}

            current_question = questions[curr_idx]

            evaluation = self.evaluate_interview_answer(
                role=session.target_role,
                difficulty=session.difficulty,
                question=current_question,
                answer=answer
            )

            # Record turn
            current_turns = session.turns
            current_turns.append({
                "question_id": current_question.get("id", curr_idx + 1),
                "type": current_question.get("type", "general"),
                "question": current_question.get("question"),
                "answer": answer,
                "evaluation": evaluation,
                "answered_at": datetime.now(timezone.utc).isoformat()
            })
            session.turns = current_turns

            next_idx = curr_idx + 1
            session.current_question_index = next_idx

            if next_idx >= len(questions):
                session.status = "completed"
                final_report = self._generate_final_report(session)
                session.final_report = final_report
                db.commit()

                return {
                    "success": True,
                    "status": "completed",
                    "turn_evaluation": evaluation,
                    "final_report": final_report,
                    "message": "Interview completed! You can now review your comprehensive performance report."
                }
            else:
                db.commit()
                next_question = questions[next_idx]
                return {
                    "success": True,
                    "status": "in_progress",
                    "turn_evaluation": evaluation,
                    "current_question_index": next_idx,
                    "total_questions": len(questions),
                    "next_question": next_question
                }
        except Exception as e:
            db.rollback()
            logger.error(f"Error submitting interview answer: {e}")
            raise
        finally:
            db.close()

    def get_session(self, session_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """Retrieves an interview session with full details."""
        db = SessionLocal()
        try:
            session = db.query(InterviewSession).filter_by(id=session_id, user_id=user_id).first()
            return session.to_dict() if session else None
        finally:
            db.close()

    def get_user_sessions(self, user_id: int) -> List[Dict[str, Any]]:
        """Lists all interview sessions for a user, ordered from newest to oldest."""
        db = SessionLocal()
        try:
            sessions = db.query(InterviewSession).filter_by(user_id=user_id).order_by(InterviewSession.created_at.desc()).all()
            return [s.to_dict() for s in sessions]
        finally:
            db.close()


interview_service = InterviewService()
