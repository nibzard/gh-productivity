"""Process and aggregate collected data."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from rich.console import Console

from .ai_detector import detect_ai

console = Console()


def load_raw_data(raw_dir: Path) -> list[dict]:
    """Load all raw JSON files from directory."""
    data = []

    for file in raw_dir.glob("*.json"):
        if file.name == "summary.json":
            continue

        with open(file) as f:
            data.append(json.load(f))

    return data


def process_commits(commits: list[dict]) -> pd.DataFrame:
    """Process commits into DataFrame with AI detection."""
    if not commits:
        return pd.DataFrame()

    rows = []

    for c in commits:
        ai_info = detect_ai(
            c.get("message", ""),
            c.get("author_name", ""),
            c.get("author_email", ""),
            datetime.fromisoformat(c["date"].replace("Z", "+00:00")),
        )

        rows.append({
            "sha": c["sha"],
            "date": pd.to_datetime(c["date"]),
            "message": c["message"],
            "author_name": c["author_name"],
            "author_email": c["author_email"],
            "additions": c.get("additions", 0),
            "deletions": c.get("deletions", 0),
            "files": c.get("files", 0),
            "is_ai_assisted": ai_info.is_ai_assisted,
            "ai_agent": ai_info.ai_agent,
            "ai_confidence": ai_info.confidence,
        })

    return pd.DataFrame(rows)


def process_prs(prs: list[dict]) -> pd.DataFrame:
    """Process pull requests into DataFrame."""
    if not prs:
        return pd.DataFrame()

    rows = []

    for pr in prs:
        rows.append({
            "number": pr["number"],
            "created": pd.to_datetime(pr["created"]),
            "closed": pd.to_datetime(pr["closed"]) if pr.get("closed") else None,
            "merged": pd.to_datetime(pr["merged"]) if pr.get("merged") else None,
            "state": pr["state"],
            "additions": pr["additions"],
            "deletions": pr["deletions"],
            "changed_files": pr["changed_files"],
        })

    return pd.DataFrame(rows)


def aggregate_data(
    raw_dir: Path,
    output_dir: Path,
    exclude_forks: bool = True,
    year: int | None = None,
) -> dict[str, pd.DataFrame]:
    """
    Aggregate all collected data into DataFrames.

    Args:
        raw_dir: Directory with raw JSON files (can be year-specific like data/raw/2025)
        output_dir: Directory to save parquet files (year-specific subdir created if year specified)
        exclude_forks: Filter out forked repos from analysis
        year: Optional year for creating year-specific output directory

    Returns:
        Dict with DataFrames: commits, prs, repos
    """
    # Create year-specific output directory if year provided
    if year:
        output_dir = output_dir / str(year)

    output_dir.mkdir(parents=True, exist_ok=True)
    raw_data = load_raw_data(raw_dir)

    console.print(f"[cyan]Processing {len(raw_data)} repos...[/cyan]")

    all_commits = []
    all_prs = []
    repo_stats = []

    for repo_data in raw_data:
        # Skip forks if requested (for safety, even if collect already filtered)
        if exclude_forks and repo_data.get("fork", False):
            continue
        owner = repo_data["owner"]
        name = repo_data["name"]

        # Process commits
        commits_df = process_commits(repo_data.get("commits", []))
        if not commits_df.empty:
            commits_df["repo"] = repo_data["full_name"]
            commits_df["owner"] = owner
            all_commits.append(commits_df)

        # Process PRs
        prs_df = process_prs(repo_data.get("prs", []))
        if not prs_df.empty:
            prs_df["repo"] = repo_data["full_name"]
            all_prs.append(prs_df)

        # Repo stats
        commit_count = len(repo_data.get("commits", []))
        pr_count = len(repo_data.get("prs", []))
        ai_count = commits_df["is_ai_assisted"].sum() if not commits_df.empty else 0

        repo_stats.append({
            "name": name,
            "owner": owner,
            "full_name": repo_data["full_name"],
            "private": repo_data["private"],
            "fork": repo_data["fork"],
            "language": repo_data.get("language"),
            "commits_2025": commit_count,
            "prs_2025": pr_count,
            "ai_commits": int(ai_count),
            "additions": int(commits_df["additions"].sum()) if not commits_df.empty else 0,
            "deletions": int(commits_df["deletions"].sum()) if not commits_df.empty else 0,
            "net_lines": int(commits_df["additions"].sum() - commits_df["deletions"].sum()) if not commits_df.empty else 0,
        })

    # Combine all
    commits_df = pd.concat(all_commits, ignore_index=True) if all_commits else pd.DataFrame()
    prs_df = pd.concat(all_prs, ignore_index=True) if all_prs else pd.DataFrame()
    repos_df = pd.DataFrame(repo_stats)

    # Save to parquet
    if not commits_df.empty:
        commits_df.to_parquet(output_dir / "commits.parquet", index=False)
        console.print(f"[green]✓[/green] Saved {len(commits_df)} commits")

    if not prs_df.empty:
        prs_df.to_parquet(output_dir / "prs.parquet", index=False)
        console.print(f"[green]✓[/green] Saved {len(prs_df)} PRs")

    repos_df.to_parquet(output_dir / "repos.parquet", index=False)
    console.print(f"[green]✓[/green] Saved {len(repos_df)} repos")

    return {
        "commits": commits_df,
        "prs": prs_df,
        "repos": repos_df,
    }


def calculate_language_stats(commits_df: pd.DataFrame, repos_df: pd.DataFrame) -> pd.DataFrame:
    """Calculate language statistics."""
    if repos_df.empty:
        return pd.DataFrame()

    # Language breakdown from repos
    lang_stats = repos_df.groupby("language").agg({
        "commits_2025": "sum",
        "additions": "sum",
        "net_lines": "sum",
    }).reset_index()

    lang_stats = lang_stats.sort_values("additions", ascending=False)
    return lang_stats


def calculate_temporal_stats(commits_df: pd.DataFrame) -> dict:
    """Calculate temporal productivity stats."""
    if commits_df.empty:
        return {}

    commits_df["date_only"] = commits_df["date"].dt.date
    commits_df["week"] = commits_df["date"].dt.isocalendar().week
    commits_df["month"] = commits_df["date"].dt.month
    commits_df["day_of_week"] = commits_df["date"].dt.dayofweek
    commits_df["hour"] = commits_df["date"].dt.hour

    return {
        "commits_by_date": commits_df.groupby("date_only").size().to_dict(),
        "commits_by_week": commits_df.groupby("week").size().to_dict(),
        "commits_by_month": commits_df.groupby("month").size().to_dict(),
        "commits_by_day_of_week": commits_df.groupby("day_of_week").size().to_dict(),
        "commits_by_hour": commits_df.groupby("hour").size().to_dict(),
    }
