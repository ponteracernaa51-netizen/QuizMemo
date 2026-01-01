from .basic import BasicCard
from .quiz import QuizCard

# Registry instance
CARD_TYPES = {
    'basic': BasicCard(),
    'quiz': QuizCard()
}

def get_card_type(code: str):
    return CARD_TYPES.get(code)

def get_all_types():
    return [ct for ct in CARD_TYPES.values()]
