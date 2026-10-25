"""
mailsys.spam.filter
===================
Keyword-based spam filtering and scoring.

Scans the subject and body of incoming emails against a configurable keyword list.
If the score meets or exceeds `settings.spam_threshold`, the email is flagged as spam
and routed to `Spam/new/` instead of `new/`.
"""
from __future__ import annotations

from pathlib import Path

from mailsys.common.logger import get_logger
from mailsys.config.settings import settings
from mailsys.mime.message_builder import get_html_body, get_text_body, parse_message

logger = get_logger(__name__)
_KEYWORDS_PATH = Path(__file__).parent / "keywords.txt"


class SpamFilter:
    """Keyword-based spam scorer.

    Loads the keyword list from disk once at instantiation. Call reload() to refresh
    without restarting the server.
    """

    def __init__(
        self,
        keywords_path: Path = _KEYWORDS_PATH,
        threshold: int | None = None,
    ) -> None:
        """Initialize SpamFilter with a keywords file and optional threshold.

        Args:
            keywords_path: Path to file containing spam keywords.
            threshold: Optional score threshold. Defaults to settings.spam_threshold.
        """
        self.keywords_path = keywords_path
        self.keywords: list[str] = []
        self._custom_threshold = threshold
        self.reload()

    @property
    def threshold(self) -> int:
        """Return the active score threshold for flagging spam."""
        if self._custom_threshold is not None:
            return self._custom_threshold
        return getattr(settings, "spam_threshold", 5)

    @threshold.setter
    def threshold(self, value: int) -> None:
        """Set a custom score threshold."""
        self._custom_threshold = value

    def reload(self) -> None:
        """(Re-)load keywords from file. Thread-safe via GIL on list assignment."""
        if not self.keywords_path.exists():
            logger.warning("Keywords file not found: %s", self.keywords_path)
            self.keywords = []
            return

        lines = self.keywords_path.read_text(encoding="utf-8").splitlines()
        self.keywords = [
            line.strip().lower()
            for line in lines
            if line.strip() and not line.strip().startswith("#")
        ]
        logger.info("Spam filter loaded %d keywords from %s", len(self.keywords), self.keywords_path)

    def score_message(self, raw: bytes) -> tuple[int, bool]:
        """Score a raw message against the keyword list.

        Args:
            raw: Raw email bytes.

        Returns:
            tuple[int, bool]: (score, is_spam) where is_spam is True if score >= threshold.
        """
        try:
            msg = parse_message(raw)
            subject = (msg.get("Subject") or "").lower()
            body = get_text_body(msg)
            if not body:
                body = get_html_body(msg) or ""
            text = f"{subject} {body.lower()}"
        except Exception:
            logger.exception("Error parsing message for spam scoring")
            return 0, False

        score = sum(text.count(kw) for kw in self.keywords)
        is_spam = score >= self.threshold
        logger.debug("Scored message: score=%d (threshold=%d, is_spam=%s)", score, self.threshold, is_spam)
        return score, is_spam


# Module-level singleton
spam_filter = SpamFilter()
