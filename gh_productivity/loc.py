"""Lines of Code analysis using tokei."""

import json
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pandas as pd
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn

console = Console()


@dataclass
class LOCResult:
    """Result of LOC analysis for a single repo."""
    repo: str
    total_lines: int
    code_lines: int
    comments: int
    blanks: int
    by_language: dict
    scanned: bool


def check_tokei_installed() -> bool:
    """Check if tokei is installed."""
    try:
        result = subprocess.run(
            ["tokei", "--version"],
            capture_output=True,
            timeout=10
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def shallow_clone_repo(url: str, target_dir: Path, timeout_sec: int = 120) -> bool:
    """Shallow clone a git repository.

    Args:
        url: Git clone URL (https://github.com/owner/repo.git)
        target_dir: Directory to clone to
        timeout_sec: Timeout in seconds

    Returns:
        True if successful, False otherwise
    """
    cmd = ["git", "clone", "--depth", "1", "--no-tags", "--quiet", url, str(target_dir)]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=timeout_sec,
            text=True
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        return False
    except Exception:
        return False


def run_tokei(repo_path: Path) -> Optional[dict]:
    """Run tokei and parse JSON output.

    Args:
        repo_path: Path to repository

    Returns:
        Parsed tokei output or None if failed
    """
    cmd = ["tokei", str(repo_path), "--output", "json", "--files"]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=60,
            text=True
        )
        if result.returncode != 0:
            return None
        return json.loads(result.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception):
        return None


def analyze_repo_loc(owner: str, repo: str, clone_url: str) -> LOCResult:
    """Analyze LOC for a single repo: clone -> tokei -> delete.

    Args:
        owner: Repository owner
        repo: Repository name
        clone_url: HTTPS clone URL

    Returns:
        LOCResult with analysis results
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir) / repo

        # Try to clone
        if not shallow_clone_repo(clone_url, repo_path):
            return LOCResult(
                repo=f"{owner}/{repo}",
                total_lines=0,
                code_lines=0,
                comments=0,
                blanks=0,
                by_language={},
                scanned=False
            )

        # Run tokei
        tokei_result = run_tokei(repo_path)
        if not tokei_result:
            return LOCResult(
                repo=f"{owner}/{repo}",
                total_lines=0,
                code_lines=0,
                comments=0,
                blanks=0,
                by_language={},
                scanned=False
            )

        # Parse tokei output
        total = tokei_result.get("Total", {})
        by_lang = tokei_result.get("Languages", {})

        # Extract language breakdown (code only)
        lang_breakdown = {}
        for lang, data in by_lang.items():
            if isinstance(data, dict):
                lang_breakdown[lang] = data.get("code", 0)
            elif isinstance(data, int):
                lang_breakdown[lang] = data

        return LOCResult(
            repo=f"{owner}/{repo}",
            total_lines=total.get("lines", 0),
            code_lines=total.get("code", 0),
            comments=total.get("comments", 0),
            blanks=total.get("blanks", 0),
            by_language=lang_breakdown,
            scanned=True
        )


def batch_loc_analysis(
    repos_df: pd.DataFrame,
    output_dir: Path,
    limit: Optional[int] = None,
) -> pd.DataFrame:
    """Analyze LOC for all non-fork repos.

    Args:
        repos_df: DataFrame of repos (from repos.parquet)
        output_dir: Directory to save results
        limit: Optional limit on number of repos to analyze

    Returns:
        DataFrame with LOC results
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Filter out forks and repos without commits
    active_repos = repos_df[(repos_df["fork"] == False) & (repos_df["commits_2025"] > 0)]

    if limit:
        active_repos = active_repos.head(limit)

    results = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        task = progress.add_task(
            "[cyan]Analyzing LOC...",
            total=len(active_repos)
        )

        for _, row in active_repos.iterrows():
            owner = row["owner"]
            name = row["name"]

            progress.update(
                task,
                description=f"[cyan]Analyzing {owner}/{name}..."
            )

            # Construct clone URL
            clone_url = f"https://github.com/{row['full_name']}.git"
            result = analyze_repo_loc(owner, name, clone_url)

            results.append({
                "repo": result.repo,
                "total_loc": result.total_lines,
                "code_loc": result.code_lines,
                "comments": result.comments,
                "blanks": result.blanks,
                "by_language": json.dumps(result.by_language),
                "scanned": result.scanned
            })

            if result.scanned:
                console.print(
                    f"[green]✓[/green] {result.repo}: "
                    f"{result.code_lines:,} code lines"
                )
            else:
                console.print(f"[red]✗[/red] {result.repo}: Failed to scan")

            progress.update(task, advance=1)

    df = pd.DataFrame(results)
    df.to_parquet(output_dir / "loc.parquet", index=False)

    # Print summary
    scanned_count = df["scanned"].sum()
    total_code = df[df["scanned"]]["code_loc"].sum()

    console.print(f"\n[bold]LOC Analysis Summary:[/bold]")
    console.print(f"  Repos scanned: {scanned_count}/{len(df)}")
    console.print(f"  Total code lines: {total_code:,}")
    console.print(f"  Results saved to: {output_dir / 'loc.parquet'}")

    return df


def get_top_languages_by_loc(loc_df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """Get top languages by total lines of code.

    Args:
        loc_df: DataFrame from LOC analysis
        top_n: Number of top languages to return

    Returns:
        DataFrame with language breakdown
    """
    if loc_df.empty:
        return pd.DataFrame()

    # Aggregate by_language across all repos
    all_languages = {}

    for _, row in loc_df.iterrows():
        if not row["scanned"]:
            continue

        by_lang = json.loads(row["by_language"])
        for lang, loc in by_lang.items():
            all_languages[lang] = all_languages.get(lang, 0) + loc

    # Convert to DataFrame and sort
    lang_df = pd.DataFrame([
        {"language": lang, "code_loc": loc}
        for lang, loc in all_languages.items()
    ]).sort_values("code_loc", ascending=False).head(top_n)

    return lang_df
