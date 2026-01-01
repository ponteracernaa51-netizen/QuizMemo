from .base import BaseCardType

class BasicCard(BaseCardType):
    @property
    def code(self) -> str:
        return "basic"

    @property
    def name(self) -> str:
        return "Basic (Flashcard)"

    def get_import_instructions(self) -> str:
        return """
        <code style="display:block; padding:5px; background:rgba(0,0,0,0.3); border-radius:3px;">Question | CorrectAnswer</code>
        """

    def parse_row(self, row) -> dict:
        return {
            "question_text": str(row['Question']),
            "correct_answer": str(row['CorrectAnswer']),
            "options": ["nan", "nan", "nan", "nan"] # Placeholder for consistency
        }
    
    def validate(self, data: dict) -> tuple[bool, str]:
        if not data.get('question_text'): return False, "Question is required"
        if not data.get('correct_answer'): return False, "Answer is required"
        return True, ""
