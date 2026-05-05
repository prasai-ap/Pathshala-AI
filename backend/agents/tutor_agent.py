"""
Tutor Agent - Answers student questions with pedagogical approach
Provides explanations, examples, and guidance
"""


class TutorAgent:
    """Agent for providing tutoring responses to student questions"""
    
    def __init__(self, llm_client, retriever_agent):
        """
        Initialize tutor agent
        
        Args:
            llm_client: LLM client for generating responses
            retriever_agent: Retriever agent for getting context
        """
        self.llm = llm_client
        self.retriever = retriever_agent
    
    async def answer_question(self, question: str, student_id: str, language: str):
        """
        Answer a student question
        
        Args:
            question: Student's question
            student_id: ID of the student
            language: Language preference (Nepali/English)
        
        Returns:
            Tutoring response with explanation and examples
        """
        # Retrieve context
        contexts = await self.retriever.retrieve_context(question, top_k=5)
        context_texts = [c.get("content") for c in contexts if c.get("content")]

        # Build instruction: use textbook context only and return JSON
        system_msg = {
            "role": "system",
            "content": (
                "You are a primary-school tutor. Use only the provided textbook excerpts "
                "to answer the student's question. Do NOT hallucinate. If the textbook "
                "context is insufficient to answer, say so clearly. Keep explanations very "
                "simple, as if teaching a child. Return a JSON object with keys: "
                "answer_english and answer_nepali."
            )
        }

        user_content = f"Question: {question}\n\nTextbook excerpts:\n"
        for i, t in enumerate(context_texts, 1):
            user_content += f"[{i}] {t}\n\n"

        user_msg = {"role": "user", "content": user_content}

        # Call LLM
        try:
            resp = self.llm.generate(messages=[system_msg, user_msg], max_tokens=400, temperature=0.2)
        except Exception as e:
            return {"answer_english": "", "answer_nepali": "", "error": str(e)}

        # Extract text from response
        text = ""
        try:
            # Chat-style response
            choices = resp.get("choices", [])
            if choices:
                first = choices[0]
                if isinstance(first.get("message"), dict):
                    text = first["message"].get("content", "")
                else:
                    text = first.get("text") or first.get("message") or ""
            else:
                text = resp.get("choices_text") or ""
        except Exception:
            text = str(resp)

        # Try to parse JSON in the output
        import json
        answer_english = ""
        answer_nepali = ""
        try:
            # Sometimes assistants include code blocks; find first JSON object
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                j = json.loads(text[start:end+1])
                answer_english = j.get("answer_english", "")
                answer_nepali = j.get("answer_nepali", "")
            else:
                # Fallback: split by delimiter lines (English then Nepali)
                parts = text.split("\n\n")
                if len(parts) >= 2:
                    answer_english = parts[0].strip()
                    answer_nepali = parts[1].strip()
                else:
                    answer_english = text.strip()
                    answer_nepali = ""
        except Exception:
            answer_english = text.strip()
            answer_nepali = ""

        return {"answer_english": answer_english, "answer_nepali": answer_nepali, "retrieved": contexts}
