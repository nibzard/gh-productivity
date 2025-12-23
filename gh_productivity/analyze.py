"""Calculate productivity metrics."""

from dataclasses import dataclass
from datetime import datetime

import pandas as pd
from rich.console import Console
from rich.table import Table

console = Console()


@dataclass
class ProductivityMetrics:
    """Container for productivity metrics."""

    # Volume
    total_commits: int = 0
    total_additions: int = 0
    total_deletions: int = 0
    net_lines: int = 0
    files_touched: int = 0

    # Repos
    repos_active: int = 0
    repos_created: int = 0
    most_active_repo: str = ""

    # Temporal
    coding_days: int = 0
    longest_streak: int = 0
    commits_per_day: float = 0.0

    # PRs
    prs_opened: int = 0
    prs_merged: int = 0
    avg_pr_merge_time_hours: float = 0.0

    # AI
    ai_commits: int = 0
    ai_ratio: float = 0.0
    primary_ai_agent: str = "N/A"

    # Language
    primary_language: str = "N/A"
    language_diversity: int = 0

    def print_summary(self):
        """Print metrics summary as table."""
        table = Table(title="2025 Productivity Summary")

        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Total Commits", str(self.total_commits))
        table.add_row("Net Lines Written", str(self.net_lines))
        table.add_row("Active Repos", str(self.repos_active))
        table.add_row("Coding Days", str(self.coding_days))
        table.add_row("Longest Streak", f"{self.longest_streak} days")
        table.add_row("PRs Merged", str(self.prs_merged))
        table.add_row("AI-Assisted Commits", f"{self.ai_commits} ({self.ai_ratio:.1%})")
        table.add_row("Primary AI Agent", self.primary_ai_agent)
        table.add_row("Primary Language", self.primary_language)

        console.print(table)


def calculate_metrics(
    commits_df: pd.DataFrame,
    prs_df: pd.DataFrame,
    repos_df: pd.DataFrame,
    year: int = 2025,
) -> ProductivityMetrics:
    """
    Calculate all productivity metrics.

    Args:
        commits_df: Commits DataFrame
        prs_df: Pull requests DataFrame
        repos_df: Repos DataFrame
        year: Year to analyze

    Returns:
        ProductivityMetrics object
    """
    metrics = ProductivityMetrics()

    if commits_df.empty:
        console.print("[yellow]No commits found for analysis[/yellow]")
        return metrics

    # Volume metrics
    metrics.total_commits = len(commits_df)
    metrics.total_additions = int(commits_df["additions"].sum())
    metrics.total_deletions = int(commits_df["deletions"].sum())
    metrics.net_lines = metrics.total_additions - metrics.total_deletions
    metrics.files_touched = int(commits_df["files"].sum())

    # Repo metrics
    if not repos_df.empty:
        metrics.repos_active = int((repos_df["commits_2025"] > 0).sum())

        most_active = repos_df.nlargest(1, "commits_2025")
        if not most_active.empty:
            metrics.most_active_repo = most_active.iloc[0]["full_name"]

    # Temporal metrics
    commits_df["date_only"] = commits_df["date"].dt.date
    metrics.coding_days = commits_df["date_only"].nunique()

    # Calculate streak
    dates = sorted(commits_df["date_only"].unique())
    streak = 1
    max_streak = 1

    for i in range(1, len(dates)):
        if (dates[i] - dates[i - 1]).days == 1:
            streak += 1
        else:
            max_streak = max(max_streak, streak)
            streak = 1

    metrics.longest_streak = max(max_streak, streak)
    metrics.commits_per_day = metrics.total_commits / max(metrics.coding_days, 1)

    # PR metrics
    if not prs_df.empty:
        metrics.prs_opened = len(prs_df)
        merged_prs = prs_df[prs_df["merged"].notna()]
        metrics.prs_merged = len(merged_prs)

        if not merged_prs.empty:
            merge_times = (merged_prs["merged"] - merged_prs["created"]).dt.total_seconds() / 3600
            metrics.avg_pr_merge_time_hours = float(merge_times.mean())

    # AI metrics
    ai_df = commits_df[commits_df["is_ai_assisted"] == True]
    metrics.ai_commits = len(ai_df)
    metrics.ai_ratio = metrics.ai_commits / max(metrics.total_commits, 1)

    if not ai_df.empty:
        agent_counts = ai_df["ai_agent"].value_counts()
        if not agent_counts.empty:
            metrics.primary_ai_agent = agent_counts.index[0]

    # Language metrics
    if not repos_df.empty:
        lang_counts = repos_df.groupby("language")["commits_2025"].sum()
        lang_counts = lang_counts[lang_counts > 0].sort_values(ascending=False)

        if not lang_counts.empty:
            metrics.primary_language = lang_counts.index[0]
            metrics.language_diversity = len(lang_counts)

    return metrics


def calculate_ai_breakdown(commits_df: pd.DataFrame) -> dict:
    """Calculate AI assistance breakdown by agent and time."""
    if commits_df.empty:
        return {}

    ai_commits = commits_df[commits_df["is_ai_assisted"] == True]

    if ai_commits.empty:
        return {"total": 0, "by_agent": {}, "by_month": {}}

    # By agent
    by_agent = ai_commits["ai_agent"].value_counts().to_dict()

    # By month
    ai_commits["month"] = ai_commits["date"].dt.to_period("M")
    by_month = ai_commits.groupby("month").size().to_dict()
    by_month = {str(k): v for k, v in by_month.items()}

    return {
        "total": len(ai_commits),
        "by_agent": by_agent,
        "by_month": by_month,
    }


def calculate_repo_productivity(repos_df: pd.DataFrame) -> pd.DataFrame:
    """Calculate per-repo productivity ranking."""
    if repos_df.empty:
        return pd.DataFrame()

    ranked = repos_df[
        ["full_name", "commits_2025", "net_lines", "ai_commits", "language"]
    ].copy()

    ranked["ai_ratio"] = ranked["ai_commits"] / ranked["commits_2025"].replace(0, 1)
    ranked = ranked.sort_values("commits_2025", ascending=False)

    return ranked
