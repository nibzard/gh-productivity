"""Command-line interface."""

import json
from pathlib import Path

import click
from rich.console import Console

from .collect import collect_repos
from .process import aggregate_data
from .analyze import calculate_metrics, calculate_ai_breakdown, calculate_repo_productivity
from .visualize import generate_all_visualizations

console = Console()


@click.group()
@click.version_option(version="0.1.0")
def main():
    """GitHub productivity analysis tool with AI collaboration detection."""
    pass


@main.command()
@click.option("--year", default=2025, help="Year to analyze")
@click.option("--repos", default="repos.json", help="Path to repos.json file")
@click.option("--output", default="data/raw", help="Output directory for raw data")
@click.option("--author", help="Filter by author (email or username)")
def collect(year: int, repos: str, output: str, author: str | None):
    """Collect data from GitHub API."""
    repos_path = Path(repos)
    output_path = Path(output)

    if not repos_path.exists():
        console.print(f"[red]Error: {repos} not found[/red]")
        return

    console.print(f"\n[cyan]Collecting data for {year}...[/cyan]\n")

    collect_repos(repos_path, year, output_path, author)


@main.command()
@click.option("--data", default="data/raw", help="Raw data directory")
@click.option("--output", default="data/processed", help="Output directory")
def process(data: str, output: str):
    """Process and aggregate collected data."""
    from . import process as proc_module

    data_path = Path(data)
    output_path = Path(output)

    if not data_path.exists():
        console.print(f"[red]Error: {data} not found[/red]")
        return

    console.print(f"\n[cyan]Processing data...[/cyan]\n")

    proc_module.aggregate_data(data_path, output_path)


@main.command()
@click.option("--data", default="data/processed", help="Processed data directory")
def analyze(data: str):
    """Analyze productivity metrics."""
    import pandas as pd

    data_path = Path(data)

    commits_path = data_path / "commits.parquet"
    prs_path = data_path / "prs.parquet"
    repos_path = data_path / "repos.parquet"

    if not commits_path.exists():
        console.print(f"[red]Error: No processed data found. Run 'gh-productivity process' first.[/red]")
        return

    commits_df = pd.read_parquet(commits_path)
    prs_df = pd.read_parquet(prs_path) if prs_path.exists() else pd.DataFrame()
    repos_df = pd.read_parquet(repos_path)

    console.print("\n[cyan]Analyzing productivity...[/cyan]\n")

    metrics = calculate_metrics(commits_df, prs_df, repos_df)

    console.print()
    metrics.print_summary()

    # AI breakdown
    ai_breakdown = calculate_ai_breakdown(commits_df)
    console.print(f"\n[bold]AI Breakdown:[/bold]")
    console.print(f"  Total AI commits: {ai_breakdown.get('total', 0)}")

    if ai_breakdown.get("by_agent"):
        console.print(f"  By agent:")
        for agent, count in ai_breakdown["by_agent"].items():
            console.print(f"    - {agent}: {count}")


@main.command()
@click.option("--data", default="data/processed", help="Processed data directory")
@click.option("--output", default="plots", help="Output directory for plots")
def visualize(data: str, output: str):
    """Generate visualizations."""
    import pandas as pd

    data_path = Path(data)
    output_path = Path(output)

    commits_path = data_path / "commits.parquet"
    prs_path = data_path / "prs.parquet"
    repos_path = data_path / "repos.parquet"

    if not commits_path.exists():
        console.print(f"[red]Error: No processed data found. Run 'gh-productivity process' first.[/red]")
        return

    commits_df = pd.read_parquet(commits_path)
    prs_df = pd.read_parquet(prs_path) if prs_path.exists() else pd.DataFrame()
    repos_df = pd.read_parquet(repos_path)

    generate_all_visualizations(commits_df, prs_df, repos_df, output_path)


@main.command()
@click.option("--year", default=2025, help="Year to analyze")
@click.option("--repos", default="repos.json", help="Path to repos.json file")
@click.option("--author", help="Filter by author")
def run(year: int, repos: str, author: str | None):
    """Run full pipeline: collect, process, analyze, visualize."""
    repos_path = Path(repos)
    raw_dir = Path("data/raw")
    processed_dir = Path("data/processed")
    plots_dir = Path("plots")

    console.print(f"\n[bold cyan]GitHub Productivity Analysis {year}[/bold cyan]\n")

    # Step 1: Collect
    if not raw_dir.exists() or not list(raw_dir.glob("*.json")):
        console.print("[cyan]Step 1: Collecting data...[/cyan]")
        collect_repos(repos_path, year, raw_dir, author)
    else:
        console.print("[yellow]Step 1: Skipping collection (data already exists)[/yellow]")

    # Step 2: Process
    console.print("\n[cyan]Step 2: Processing data...[/cyan]")
    from . import process as proc_module
    dfs = proc_module.aggregate_data(raw_dir, processed_dir)

    # Step 3: Analyze
    console.print("\n[cyan]Step 3: Analyzing...[/cyan]")
    metrics = calculate_metrics(dfs["commits"], dfs["prs"], dfs["repos"])
    console.print()
    metrics.print_summary()

    # Step 4: Visualize
    console.print("\n[cyan]Step 4: Generating visualizations...[/cyan]")
    generate_all_visualizations(dfs["commits"], dfs["prs"], dfs["repos"], plots_dir)

    console.print(f"\n[bold green]✓ Analysis complete![/bold green]")
    console.print(f"  Plots: {plots_dir.absolute()}")
    console.print(f"  Data: {processed_dir.absolute()}")


if __name__ == "__main__":
    main()
