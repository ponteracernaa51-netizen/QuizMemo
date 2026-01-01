from abc import ABC, abstractmethod

class BaseCardType(ABC):
    @property
    @abstractmethod
    def code(self) -> str:
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def get_import_instructions(self) -> str:
        """Returns HTML or text instructions for importing this card type."""
        pass

    @abstractmethod
    def parse_row(self, row) -> dict:
        """Parses a pandas row into a dictionary for the 'questions' table."""
        pass
    
    @abstractmethod
    def validate(self, data: dict) -> tuple[bool, str]:
        """Validates the data dictionary. Returns (is_valid, error_message)."""
        pass
