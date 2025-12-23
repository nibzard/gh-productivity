"""Collect data from GitHub API."""

import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn
from tqdm import tqdm

console = Console()


def gh_api(endpoint: str, paginate: bool = False) -> Any:
    """Call GitHub API via gh CLI."""
    cmd = ["gh", "api", endpoint]

    if paginate:
        cmd.append("--paginate")

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, check=True, timeout=60
        )
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        console.print(f"[red]API error: {e.stderr}[/red]")
        return None
    except subprocess.TimeoutExpired:
        console.print(f"[red]Timeout for: {endpoint}[/red]")
        return None


def fetch_commits(owner: str, repo: str, since: str, author: str | None = None) -> list[dict]:
    """Fetch commits since a date, optionally filtered by author."""
    endpoint = f"repos/{owner}/{repo}/commits?since={since}&per_page=100"

    if author:
        endpoint += f"&author={author}"

    commits = gh_api(endpoint, paginate=True)

    if not commits:
        return []

    # Extract relevant fields
    result = []
    for c in commits:
        result.append({
            "sha": c["sha"],
            "date": c["commit"]["committer"]["date"],
            "message": c["commit"]["message"],
            "author_name": c["commit"]["author"]["name"],
            "author_email": c["commit"]["author"]["email"],
            "additions": c.get("stats", {}).get("additions", 0),
            "deletions": c.get("stats", {}).get("deletions", 0),
            "files": len(c.get("files", [])),
        })

    return result


def fetch_prs(owner: str, repo: str, since: str) -> list[dict]:
    """Fetch pull requests since a date."""
    endpoint = f"repos/{owner}/{repo}/pulls?state=all&per_page=100&sort=created&direction=desc"

    prs = gh_api(endpoint, paginate=True)

    if not prs:
        return []

    # Filter by date
    since_dt = datetime.fromisoformat(since)
    result = []

    for pr in prs:
        created = datetime.fromisoformat(pr["created_at"].replace("Z", "+00:00"))
        if created < since_dt:
            continue

        result.append({
            "number": pr["number"],
            "created": pr["created_at"],
            "closed": pr.get("closed_at"),
            "merged": pr.get("merged_at"),
            "state": pr["state"],
            "additions": pr.get("additions", 0),
            "deletions": pr.get("deletions", 0),
            "changed_files": pr.get("changed_files", 0),
        })

    return result


def fetch_languages(owner: str, repo: str) -> dict:
    """Fetch language breakdown."""
    endpoint = f"repos/{owner}/{repo}/languages"
    return gh_api(endpoint) or {}


def fetch_stats(owner: str, repo: str) -> dict:
    """Fetch repo statistics."""
    stats = {}

    # Code frequency (weekly additions/deletions)
    stats["code_frequency"] = gh_api(f"repos/{owner}/{repo}/stats/code_frequency") or []

    # Commit activity (weekly commit counts)
    stats["commit_activity"] = gh_api(f"repos/{owner}/{repo}/stats/commit_activity") or []

    # Participation (owner vs all)
    stats["participation"] = gh_api(f"repos/{owner}/{repo}/stats/participation") or {}

    return stats


def collect_repos(
    repos_json: Path,
    year: int,
    output_dir: Path,
    author: str | None = None,
) -> dict:
    """
    Collect data for all repos.

    Args:
        repos_json: Path to repos.json file
        year: Year to analyze
        output_dir: Directory to save raw data
        author: Filter by author email/username

    Returns:
        Summary dict
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(repos_json) as f:
        repos = json.load(f)

    since = f"{year}-01-01T00:00:00Z"
    summary = {"repos": len(repos), "with_commits": 0, "total_commits": 0}

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Fetching repos...", total=len(repos))

        for repo in repos:
            owner = repo["owner"]["login"]
            name = repo["name"]

            progress.update(task, description=f"[cyan]Fetching {owner}/{name}...")

            data = {
                "name": name,
                "owner": owner,
                "full_name": repo["full_name"],
                "private": repo["private"],
                "fork": repo["fork"],
                "language": repo.get("language"),
                "created_at": repo["created_at"],
            }

            # Fetch commits
            commits = fetch_commits(owner, name, since, author)
            data["commits"] = commits
            summary["total_commits"] += len(commits)

            if commits:
                summary["with_commits"] += 1

            # Fetch PRs
            data["prs"] = fetch_prs(owner, name, since)

            # Fetch languages
            data["languages"] = fetch_languages(owner, name)

            # Save to file
            safe_name = f"{owner}_{name}".replace("/", "_")
            output_file = output_dir / f"{safe_name}.json"

            with open(output_file, "w") as f:
                json.dump(data, f, indent=2)

            progress.update(task, advance=1)

    # Save summary
    with open(output_dir / "summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    console.print(f"\n[green]✓[/green] Collected data for {summary['repos']} repos")
    console.print(f"  Repos with commits: {summary['with_commits']}")
    console.print(f"  Total commits: {summary['total_commits']}")

    return summary
