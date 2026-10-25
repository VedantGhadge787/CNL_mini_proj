"""
mailsys.spam.filter
===================
Keyword-based spam filtering and scoring.

Scans the subject and body of incoming emails against a configurable keyword list.
If the score meets or exceeds `settings.spam_threshold`, the email is flagged as spam
and routed to `Spam/new/` instead of `new/`.

Imports needed:
    from pathlib import Path
    from mailsys.common.logger import get_logger
    from mailsys.config.settings import settings
    from mailsys.mime.message_builder import parse_message, get_text_body
"""
from pathlib import Path
from mailsys.common.logger import get_logger
from mailsys.config.settings import settings
from mailsys.mime.message_builder import parse_message, get_text_body

logger = get_logger(__name__)
_KEYWORDS_PATH = Path(__file__).parent / "keywords.txt"


class SpamFilter:
    """Keyword-based spam scorer.

    Loads keywords from keywords.txt and scores incoming messages.
    """

    def __init__(self, keywords_path: Path = _KEYWORDS_PATH) -> None:
        self.keywords_path = keywords_path
        self.keywords: list[str] = []
        self.threshold: int = getattr(settings, "spam_threshold", 5)
        self.reload()

    def reload(self) -> None:
        """(Re-)load keywords from file into memory.

        TODO:
            - Read lines from self.keywords_path if exists
            - Strip whitespace, lowercase, filter out '#' comments and blank lines
            - Store in self.keywords list
        """
        # TODO: Implement
        raise NotImplementedError

    def score_message(self, raw: bytes) -> tuple[int, bool]:
        """Score a raw message against the keyword list.

        Args:
            raw: Raw email bytes.

        Returns:
            tuple[int, bool]: (score, is_spam) where is_spam is True if score >= threshold.

        TODO:
            - Parse raw bytes with parse_message()
            - Extract subject and plain text body
            - Concatenate and lowercase
            - Count occurrences of each keyword
            - Return (score, score >= self.threshold)
        """
        # TODO: Implement
        raise NotImplementedError
