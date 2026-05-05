"""
Quiz Agent - Generates and evaluates quizzes
Assesses student understanding and provides feedback
"""


class QuizAgent:
    """Agent for generating and evaluating quizzes"""
    
    def __init__(self, llm_client, retriever_agent):
        """
        Initialize quiz agent
        
        Args:
            llm_client: LLM client for generating quiz questions
            retriever_agent: Retriever agent for getting topic context
        """
        self.llm = llm_client
        self.retriever = retriever_agent
    
    async def generate_quiz(self, topic: str, num_questions: int, language: str):
        """
        Generate a quiz on a given topic
        
        Args:
            topic: Quiz topic
            num_questions: Number of questions to generate
            language: Language preference (Nepali/English)
        
        Returns:
            List of quiz questions
        """
        # Retrieve supporting context
        contexts = await self.retriever.retrieve_context(topic, top_k=5)
        context_texts = [c.get("content") for c in contexts if c.get("content")]

        system_msg = {
            "role": "system",
            "content": (
                "You are a primary-school quiz-maker. Use only the provided textbook excerpts "
                "to create simple, age-appropriate multiple-choice or short-answer questions. "
                "Do NOT invent facts beyond the textbook. Return JSON: {\"quiz_questions\": [\"q1\", \"q2\", ...]}"
            )
        }

        user_content = f"Topic: {topic}\n\nTextbook excerpts:\n"
        for i, t in enumerate(context_texts, 1):
            user_content += f"[{i}] {t}\n\n"

        user_msg = {"role": "user", "content": user_content}

        try:
            resp = self.llm.generate(messages=[system_msg, user_msg], max_tokens=300, temperature=0.2)
        except Exception as e:
            return {"quiz_questions": [], "error": str(e)}

        # Extract text
        text = ""
        try:
            choices = resp.get("choices", [])
            if choices:
                first = choices[0]
                if isinstance(first.get("message"), dict):
                    text = first["message"].get("content", "")
                else:
                    text = first.get("text") or ""
            else:
                text = str(resp)
        except Exception:
            text = str(resp)

        # Parse JSON list
        import json
        quiz_questions = []
        try:
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                j = json.loads(text[start:end+1])
                quiz_questions = j.get("quiz_questions") or j.get("questions") or []
            else:
                # Fallback: take lines as questions
                lines = [l.strip() for l in text.splitlines() if l.strip()]
                # Keep first num_questions lines
                quiz_questions = lines[:num_questions]
        except Exception:
            quiz_questions = [t.strip() for t in text.splitlines() if t.strip()][:num_questions]

        return {"quiz_questions": quiz_questions, "retrieved": contexts}
    
    async def evaluate_answer(self, question: str, student_answer: str, correct_answer: str):
        """
        Evaluate a student's quiz answer
        
        Args:
            question: Quiz question
            student_answer: Student's answer
            correct_answer: Correct answer
        
        Returns:
            Evaluation with score and feedback
        """
        # TODO: Implement answer evaluation logic
        pass
