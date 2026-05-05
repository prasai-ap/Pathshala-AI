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
        # TODO: Implement question answering logic
        pass
