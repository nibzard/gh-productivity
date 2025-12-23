"""Command-line interface."""

import json
from pathlib import Path

import click
from rich.console import Console

from .collect import collect_repos
from .process import aggregate_data
from .analyze import calculate_metrics, calculate_ai_breakdown, calculate_repo_productivity
from .visualize import generate_all_visualizations
from .temporal import analyze_time_patterns

console = Console()


def print_temporal_summary(temporal_metrics):
    """Print temporal metrics summary."""
    from rich.table import Table

    table = Table(title="Temporal Patterns")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    # Peak hours
    peak_str = ", ".join([f"{h}h ({c})" for h, c in temporal_metrics.peak_hours[:3]])
    table.add_row("Peak Hours", peak_str or "N/A")

    # Chronotype
    table.add_row("Chronotype", temporal_metrics.chronotype.capitalize())

    # Work/Life
    table.add_row("Weekend Activity", f"{temporal_metrics.weekend_commit_ratio:.1%}")
    table.add_row("After-Hours (Weekdays)", f"{temporal_metrics.after_hours_percentage:.1%}")
    table.add_row("Work/Life", temporal_metrics.work_life_interpretation)

    # Sessions
    table.add_row("Total Sessions", str(temporal_metrics.session_count))
    if temporal_metrics.session_count > 0:
        table.add_row("Avg Session Duration", f"{temporal_metrics.avg_session_duration_minutes:.0f} min")
        table.add_row("Commits per Session", f"{temporal_metrics.commits_per_session:.1f}")

    # Streaks
    table.add_row("Current Streak", f"{temporal_metrics.current_streak} days")
    table.add_row("Longest Streak", f"{temporal_metrics.longest_streak} days")
    if temporal_metrics.longest_streak > 1 and temporal_metrics.longest_streak_dates[0]:
        table.add_row(
            "Longest Streak Dates",
            f"{temporal_metrics.longest_streak_dates[0]} to {temporal_metrics.longest_streak_dates[1]}"
        )
    if temporal_metrics.avg_gap_between_streaks > 0:
        table.add_row("Avg Gap Between Streaks", f"{temporal_metrics.avg_gap_between_streaks:.1f} days")

    console.print(table)


@click.group()
@click.version_option(version="0.1.0")
def main():
    """GitHub productivity analysis tool with AI collaboration detection."""
    pass


@main.command()
@click.option("--years", default="2025", help="Year(s) to analyze (comma-separated)")
@click.option("--repos", default="repos.json", help="Path to repos.json file")
@click.option("--output", default="data/raw", help="Output directory for raw data")
@click.option("--author", help="Filter by author (email or username)")
@click.option("--include-forks", is_flag=True, help="Include forked repos in analysis")
def collect(years: str, repos: str, output: str, author: str | None, include_forks: bool):
    """Collect data from GitHub API."""
    repos_path = Path(repos)
    output_path = Path(output)

    if not repos_path.exists():
        console.print(f"[red]Error: {repos} not found[/red]")
        return

    year_list = [int(y.strip()) for y in years.split(",")]
    console.print(f"\n[cyan]Collecting data for years: {year_list}[/cyan]\n")

    for year in year_list:
        collect_repos(repos_path, year, output_path, author, exclude_forks=not include_forks)


@main.command()
@click.option("--data", default="data/raw", help="Raw data directory")
@click.option("--output", default="data/processed", help="Output directory")
@click.option("--years", default="2025", help="Year(s) to process (comma-separated)")
@click.option("--include-forks", is_flag=True, help="Include forked repos in analysis")
def process(data: str, output: str, years: str, include_forks: bool):
    """Process and aggregate collected data."""
    from . import process as proc_module

    data_path = Path(data)
    output_path = Path(output)

    if not data_path.exists():
        console.print(f"[red]Error: {data} not found[/red]")
        return

    year_list = [int(y.strip()) for y in years.split(",")]
    console.print(f"\n[cyan]Processing data for years: {year_list}...[/cyan]\n")

    for year in year_list:
        year_data_path = data_path / str(year)
        if year_data_path.exists():
            proc_module.aggregate_data(year_data_path, output_path, exclude_forks=not include_forks, year=year)
        else:
            console.print(f"[yellow]Warning: No data found for {year}[/yellow]")


@main.command()
@click.option("--data", default="data/processed", help="Processed data directory")
@click.option("--years", default="2025", help="Year(s) to analyze (comma-separated)")
@click.option("--temporal", is_flag=True, help="Include temporal analysis")
def analyze(data: str, years: str, temporal: bool):
    """Analyze productivity metrics."""
    import pandas as pd

    data_path = Path(data)

    year_list = [int(y.strip()) for y in years.split(",")]
    console.print(f"\n[cyan]Analyzing productivity for years: {year_list}...[/cyan]\n")

    for year in year_list:
        year_path = data_path / str(year)
        commits_path = year_path / "commits.parquet"
        prs_path = year_path / "prs.parquet"
        repos_path = year_path / "repos.parquet"

        if not commits_path.exists():
            console.print(f"[yellow]No data found for {year}[/yellow]")
            continue

        commits_df = pd.read_parquet(commits_path)
        prs_df = pd.read_parquet(prs_path) if prs_path.exists() else pd.DataFrame()
        repos_df = pd.read_parquet(repos_path)

        console.print(f"\n[bold]--- {year} ---[/bold]")
        metrics = calculate_metrics(commits_df, prs_df, repos_df, year=year)

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

        # Temporal analysis
        if temporal:
            console.print(f"\n[bold]Temporal Patterns:[/bold]")
            temporal_metrics = analyze_time_patterns(commits_df)
            print_temporal_summary(temporal_metrics)


@main.command()
@click.option("--data", default="data/processed", help="Processed data directory")
@click.option("--output", default="plots", help="Output directory for plots")
@click.option("--years", default="2025", help="Year(s) to visualize (comma-separated)")
@click.option("--temporal", is_flag=True, help="Include temporal visualizations")
def visualize(data: str, output: str, years: str, temporal: bool):
    """Generate visualizations."""
    import pandas as pd

    data_path = Path(data)
    output_path = Path(output)

    year_list = [int(y.strip()) for y in years.split(",")]
    console.print(f"\n[cyan]Generating visualizations for years: {year_list}...[/cyan]\n")

    for year in year_list:
        year_path = data_path / str(year)
        year_output_path = output_path / str(year)
        commits_path = year_path / "commits.parquet"
        prs_path = year_path / "prs.parquet"
        repos_path = year_path / "repos.parquet"

        if not commits_path.exists():
            console.print(f"[yellow]No data found for {year}[/yellow]")
            continue

        commits_df = pd.read_parquet(commits_path)
        prs_df = pd.read_parquet(prs_path) if prs_path.exists() else pd.DataFrame()
        repos_df = pd.read_parquet(repos_path)

        generate_all_visualizations(
            commits_df,
            prs_df,
            repos_df,
            year_output_path,
            include_temporal=temporal,
        )


@main.command()
@click.option("--years", default="2025", help="Year(s) to analyze (comma-separated)")
@click.option("--repos", default="repos.json", help="Path to repos.json file")
@click.option("--author", help="Filter by author")
@click.option("--include-forks", is_flag=True, help="Include forked repos in analysis")
def run(years: str, repos: str, author: str | None, include_forks: bool):
    """Run full pipeline: collect, process, analyze, visualize."""
    import pandas as pd
    from .benchmarks import calculate_benchmarks, print_benchmark_comparison
    from .analyze import calculate_yoy_growth

    repos_path = Path(repos)
    raw_dir = Path("data/raw")
    processed_dir = Path("data/processed")
    plots_dir = Path("plots")

    year_list = [int(y.strip()) for y in years.split(",")]
    console.print(f"\n[bold cyan]GitHub Productivity Analysis {year_list}[/bold cyan]\n")

    # Step 1: Collect
    console.print("[cyan]Step 1: Collecting data...[/cyan]")
    for year in year_list:
        year_raw_dir = raw_dir / str(year)
        if not year_raw_dir.exists() or not list(year_raw_dir.glob("*.json")):
            collect_repos(repos_path, year, raw_dir, author, exclude_forks=not include_forks)

    # Step 2: Process
    console.print("\n[cyan]Step 2: Processing data...[/cyan]")
    from . import process as proc_module
    for year in year_list:
        year_raw_dir = raw_dir / str(year)
        if year_raw_dir.exists():
            proc_module.aggregate_data(year_raw_dir, processed_dir, exclude_forks=not include_forks, year=year)

    # Step 3: Analyze (collect metrics for all years)
    console.print("\n[cyan]Step 3: Analyzing...[/cyan]")
    yearly_metrics = {}
    for year in year_list:
        year_path = processed_dir / str(year)
        commits_path = year_path / "commits.parquet"
        if commits_path.exists():
            commits_df = pd.read_parquet(commits_path)
            prs_path = year_path / "prs.parquet"
            prs_df = pd.read_parquet(prs_path) if prs_path.exists() else pd.DataFrame()
            repos_df = pd.read_parquet(year_path / "repos.parquet")

            # Load LOC data if available
            loc_path = year_path / "loc.parquet"
            loc_df = pd.read_parquet(loc_path) if loc_path.exists() else None

            console.print(f"\n[bold]--- {year} ---[/bold]")
            metrics = calculate_metrics(commits_df, prs_df, repos_df, year=year, loc_df=loc_df)
            yearly_metrics[year] = metrics
            console.print()
            metrics.print_summary()

    # Calculate YoY growth if multiple years
    if len(yearly_metrics) > 1:
        console.print("\n[bold]Year-over-Year Growth:[/bold]")
        sorted_years = sorted(yearly_metrics.keys())
        for i in range(1, len(sorted_years)):
            curr_year = sorted_years[i]
            prev_year = sorted_years[i - 1]
            growth = calculate_yoy_growth(yearly_metrics[curr_year], yearly_metrics[prev_year])
            console.print(f"  {prev_year} -> {curr_year}:")
            console.print(f"    Commits: {growth['commits']:+.1%}")
            console.print(f"    LOC: {growth['loc']:+.1%}")

    # Calculate benchmarks for most recent year
    latest_year = max(year_list)
    if latest_year in yearly_metrics:
        latest_path = processed_dir / str(latest_year) / "loc.parquet"
        loc_df = pd.read_parquet(latest_path) if latest_path.exists() else None
        benchmark = calculate_benchmarks(yearly_metrics[latest_year], loc_df)
        print_benchmark_comparison(benchmark)

    # Step 4: Visualize
    console.print("\n[cyan]Step 4: Generating visualizations...[/cyan]")
    for year in year_list:
        year_path = processed_dir / str(year)
        year_plots_dir = plots_dir / str(year)
        commits_path = year_path / "commits.parquet"
        if commits_path.exists():
            commits_df = pd.read_parquet(commits_path)
            prs_path = year_path / "prs.parquet"
            prs_df = pd.read_parquet(prs_path) if prs_path.exists() else pd.DataFrame()
            repos_df = pd.read_parquet(year_path / "repos.parquet")

            # Load LOC data for trend analysis
            loc_path = year_path / "loc.parquet"
            loc_df = pd.read_parquet(loc_path) if loc_path.exists() else None

            # Prepare yearly LOC data
            yearly_loc_data = {}
            for y in year_list:
                y_loc_path = processed_dir / str(y) / "loc.parquet"
                if y_loc_path.exists():
                    yearly_loc_data[y] = pd.read_parquet(y_loc_path)

            generate_all_visualizations(
                commits_df,
                prs_df,
                repos_df,
                year_plots_dir,
                yearly_metrics=yearly_metrics if len(yearly_metrics) > 1 else None,
                benchmark=benchmark if year == latest_year else None,
                yearly_loc_data=yearly_loc_data if yearly_loc_data else None,
            )

    console.print(f"\n[bold green]✓ Analysis complete![/bold green]")
    console.print(f"  Plots: {plots_dir.absolute()}")
    console.print(f"  Data: {processed_dir.absolute()}")


if __name__ == "__main__":
    main()
