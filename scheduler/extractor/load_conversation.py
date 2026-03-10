from typing import Optional


class ConversationLoader:
    def __init__(self):
        pass

    def load_from_file(self, file_path: str) -> str:
        """Load a conversation script from a text file."""
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    def load_from_string(self, text: str) -> str:
        """Accept a raw conversation string directly."""
        return text
