"""Detect AI-assisted commits."""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional


@dataclass
class AIInfo:
    """Information about AI assistance in a commit."""

    is_ai_assisted: bool
    ai_agent: Optional[str] = None
    confidence: Literal["high", "medium", "low"] = "low"


# AI agent detection patterns
AI_PATTERNS = {
    "claude": {
        "emails": [
            r"claude@anthropic\.com",
            r"noreply@anthropic\.com",
            r"ai@anthropic\.com",
        ],
        "co_authored": [
            r"Co-Authored-By:\s*Claude\s*<[^>]*anthropic\.com>",
            r"Co-Authored-By:\s*Claude\s*<[^>]*>",
        ],
        "keywords": [
            r"Generated with (Claude Code|Claude)",
            r"🤖 Generated with",
            r"Co-Authored-By:\s*Claude",
        ],
    },
    "copilot": {
        "emails": [
            r"copilot@github\.com",
            r"ai@github\.com",
        ],
        "co_authored": [
            r"Co-Authored-By:\s*GitHub Copilot",
            r"Co-Authored-By:\s*Copilot",
        ],
        "keywords": [
            r"Generated with Copilot",
            r"Azure OpenAI",
        ],
    },
    "codex": {
        "emails": [
            r"codex@openai\.com",
            r"codex@github\.com",
        ],
        "co_authored": [
            r"Co-Authored-By:\s*Codex",
        ],
        "keywords": [
            r"Generated with Codex",
        ],
    },
    "cursor": {
        "co_authored": [
            r"Co-Authored-By:\s*Cursor",
        ],
        "keywords": [
            r"Generated with Cursor",
        ],
    },
    "aider": {
        "co_authored": [
            r"Co-Authored-By:\s*Aider",
        ],
        "keywords": [
            r"Generated with Aider",
        ],
    },
    "cline": {
        "co_authored": [
            r"Co-Authored-By:\s*Cline",
        ],
        "keywords": [
            r"Generated with Cline",
        ],
    },
    "jetbrains": {
        "emails": [
            r"ai@jetbrains\.com",
        ],
        "keywords": [
            r"AI-generated",
        ],
    },
}


def detect_ai(
    commit_message: str,
    author_name: str,
    author_email: str,
    commit_date: datetime,
) -> AIInfo:
    """
    Detect if a commit was AI-assisted.

    Args:
        commit_message: Full commit message
        author_name: Commit author name
        author_email: Commit author email
        commit_date: Commit timestamp

    Returns:
        AIInfo with detection results
    """
    full_text = f"{commit_message} {author_name} {author_email}".lower()

    for agent, patterns in AI_PATTERNS.items():
        # Check email patterns
        for email_pattern in patterns.get("emails", []):
            if re.search(email_pattern, author_email, re.IGNORECASE):
                return AIInfo(is_ai_assisted=True, ai_agent=agent, confidence="high")

        # Check co-authored patterns
        for co_author_pattern in patterns.get("co_authored", []):
            if re.search(co_author_pattern, commit_message, re.IGNORECASE):
                return AIInfo(is_ai_assisted=True, ai_agent=agent, confidence="high")

        # Check keyword patterns
        for keyword_pattern in patterns.get("keywords", []):
            if re.search(keyword_pattern, commit_message, re.IGNORECASE):
                return AIInfo(is_ai_assisted=True, ai_agent=agent, confidence="medium")

    # Fuzzy checks for lower confidence
    fuzzy_ai_keywords = ["ai-assisted", "ai generated", "llm", "gpt"]
    for keyword in fuzzy_ai_keywords:
        if keyword in full_text:
            return AIInfo(is_ai_assisted=True, ai_agent="unknown", confidence="low")

    return AIInfo(is_ai_assisted=False)


def categorize_commits(commits: list[dict]) -> dict:
    """
    Categorize commits by AI assistance.

    Args:
        commits: List of commit dicts with message, author, date

    Returns:
        Dict with counts by AI agent
    """
    categories = {"solo": 0}

    for commit in commits:
        ai_info = detect_ai(
            commit.get("message", ""),
            commit.get("author_name", ""),
            commit.get("author_email", ""),
            datetime.fromisoformat(commit["date"].replace("Z", "+00:00"))
            if isinstance(commit.get("date"), str)
            else commit.get("date", datetime.now()),
        )

        if ai_info.is_ai_assisted:
            agent = ai_info.ai_agent or "unknown"
            categories[agent] = categories.get(agent, 0) + 1
        else:
            categories["solo"] += 1

    return categories
