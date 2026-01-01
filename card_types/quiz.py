from .base import BaseCardType

class QuizCard(BaseCardType):
    @property
    def code(self) -> str:
        return "quiz"

    @property
    def name(self) -> str:
        return "Quiz (Multiple Choice)"

    def get_import_instructions(self) -> str:
        return """
        <code style="display:block; padding:5px; background:rgba(0,0,0,0.3); border-radius:3px;">Question | Option1 | Option2 | Option3 | Option4 | CorrectAnswer</code>
        """

    def parse_row(self, row) -> dict:
        return {
            "question_text": str(row['Question']),
            "correct_answer": str(row['CorrectAnswer']),
            "options": [
                str(row.get('Option1', '')),
                str(row.get('Option2', '')),
                str(row.get('Option3', '')),
                str(row.get('Option4', ''))
            ]
        }
    
    def validate(self, data: dict) -> tuple[bool, str]:
        if not data.get('question_text'): return False, "Question is required"
        if not data.get('correct_answer'): return False, "Correct Answer is required"
        
        opts = data.get('options', [])
        if not opts or len(opts) < 4: return False, "All 4 options are required"
        
        # Check if answer matches one of the options (optional strictness, but good for Quiz)
        # For now, let's keep it loose or just ensure options are present.
        if all(o == '' or o == 'nan' for o in opts):
            return False, "At least one option must be valid"
            
        return True, ""
