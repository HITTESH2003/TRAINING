"""Step 6: validation & cleaning of the assembled markdown."""

from __future__ import annotations

import re
from html.parser import HTMLParser


class _TableBalanceChecker(HTMLParser):
    """Minimal well-formedness check: every opened tag must be closed."""

    def __init__(self):
        super().__init__()
        self.stack = []
        self.ok = True

    def handle_starttag(self, tag, attrs):
        self.stack.append(tag)

    def handle_endtag(self, tag):
        if not self.stack or self.stack[-1] != tag:
            self.ok = False
        else:
            self.stack.pop()


def clean_markdown(text: str) -> str:
    # collapse runs of blank lines to at most two
    text = re.sub(r"\n{3,}", "\n\n\n", text)
    # trim trailing whitespace on each line
    text = "\n".join(line.rstrip() for line in text.splitlines())
    return text.strip() + "\n"


def find_malformed_tables(markdown_text: str) -> list[str]:
    """Returns the raw HTML of any <table>...</table> block that fails a basic tag-balance check."""
    malformed = []
    for match in re.finditer(r"<table>.*?</table>", markdown_text, flags=re.DOTALL | re.IGNORECASE):
        html = match.group(0)
        checker = _TableBalanceChecker()
        checker.feed(html)
        if not checker.ok or checker.stack:
            malformed.append(html)
    return malformed
