"""Benchmarking against average and top GitHub users."""

from dataclasses import dataclass
import pandas as pd
from rich.console import Console
from rich.table import Table

console = Console()


# Research-based baselines
AVERAGE_DEVELOPER = {
    "loc_per_year": 10_000,
    "commits_per_year": 2_000,
    "coding_days": 200,
    "prs_per_year": 50,
}

# Estimated top percentiles (based on industry research)
TOP_10_PERCENT = {
    "loc_per_year": 20_000,
    "commits_per_year": 4_000,
    "coding_days": 250,
    "prs_per_year": 100,
}

TOP_1_PERCENT = {
    "loc_per_year": 50_000,
    "commits_per_year": 10_000,
    "coding_days": 300,
    "prs_per_year": 200,
}


@dataclass
class BenchmarkResult:
    """Result of benchmark comparison."""
    user_loc: int
    user_commits: int
    user_prs: int

    # Vs average
    loc_vs_avg_pct: float
    commits_vs_avg_pct: float
    prs_vs_avg_pct: float

    # Estimated tier
    loc_tier: str
    commits_tier: str
    overall_tier: str


def calculate_benchmarks(
    metrics,
    loc_df: pd.DataFrame | None = None,
) -> BenchmarkResult:
    """Compare user against benchmarks.

    Args:
        metrics: ProductivityMetrics from analyze.py
        loc_df: Optional LOC data DataFrame

    Returns:
        BenchmarkResult with comparisons
    """
    # Get LOC from loc_df if available
    total_loc = 0
    if loc_df is not None and not loc_df.empty:
        total_loc = int(loc_df[loc_df["scanned"]]["code_loc"].sum())

    user_commits = metrics.total_commits
    user_prs = metrics.prs_merged if metrics.prs_merged else 0

    # Calculate vs average
    loc_vs_avg = total_loc / max(AVERAGE_DEVELOPER["loc_per_year"], 1)
    commits_vs_avg = user_commits / max(AVERAGE_DEVELOPER["commits_per_year"], 1)
    prs_vs_avg = user_prs / max(AVERAGE_DEVELOPER["prs_per_year"], 1)

    # Determine tiers
    loc_tier = _get_tier(total_loc, "loc")
    commits_tier = _get_tier(user_commits, "commits")

    # Overall tier (average of LOC and commits percentiles)
    avg_percentile = (loc_vs_avg + commits_vs_avg) / 2
    if avg_percentile >= 5:
        overall_tier = "Top 1%"
    elif avg_percentile >= 2:
        overall_tier = "Top 10%"
    elif avg_percentile >= 0.8:
        overall_tier = "Average"
    else:
        overall_tier = "Below Average"

    return BenchmarkResult(
        user_loc=total_loc,
        user_commits=user_commits,
        user_prs=user_prs,
        loc_vs_avg_pct=loc_vs_avg,
        commits_vs_avg_pct=commits_vs_avg,
        prs_vs_avg_pct=prs_vs_avg,
        loc_tier=loc_tier,
        commits_tier=commits_tier,
        overall_tier=overall_tier,
    )


def _get_tier(value: int, metric_type: str) -> str:
    """Get performance tier for a metric value."""
    if metric_type == "loc":
        if value >= TOP_1_PERCENT["loc_per_year"]:
            return "Top 1%"
        elif value >= TOP_10_PERCENT["loc_per_year"]:
            return "Top 10%"
        elif value >= AVERAGE_DEVELOPER["loc_per_year"] * 0.8:
            return "Average"
        else:
            return "Below Average"
    elif metric_type == "commits":
        if value >= TOP_1_PERCENT["commits_per_year"]:
            return "Top 1%"
        elif value >= TOP_10_PERCENT["commits_per_year"]:
            return "Top 10%"
        elif value >= AVERAGE_DEVELOPER["commits_per_year"] * 0.8:
            return "Average"
        else:
            return "Below Average"
    else:
        return "Unknown"


def print_benchmark_comparison(benchmark: BenchmarkResult):
    """Print benchmark comparison table."""
    table = Table(title="Benchmark Comparison (vs Average Developer)")
    table.add_column("Metric", style="cyan")
    table.add_column("You", style="green")
    table.add_column("Average", style="yellow")
    table.add_column("Ratio", style="blue")
    table.add_column("Tier", style="magenta")

    table.add_row(
        "LOC (lines)",
        f"{benchmark.user_loc:,}",
        f"{AVERAGE_DEVELOPER['loc_per_year']:,}",
        f"{benchmark.loc_vs_avg_pct:.1f}x",
        benchmark.loc_tier,
    )
    table.add_row(
        "Commits",
        f"{benchmark.user_commits:,}",
        f"{AVERAGE_DEVELOPER['commits_per_year']:,}",
        f"{benchmark.commits_vs_avg_pct:.1f}x",
        benchmark.commits_tier,
    )
    table.add_row(
        "PRs Merged",
        f"{benchmark.user_prs:,}",
        f"{AVERAGE_DEVELOPER['prs_per_year']:,}",
        f"{benchmark.prs_vs_avg_pct:.1f}x",
        "",
    )

    console.print()
    console.print(table)
    console.print(f"\n[bold]Overall Tier: {benchmark.overall_tier}[/bold]")


def calculate_historical_comparison(yearly_metrics: dict) -> pd.DataFrame:
    """Calculate year-over-year comparison.

    Args:
        yearly_metrics: Dict mapping year -> ProductivityMetrics

    Returns:
        DataFrame with YoY comparison
    """
    if not yearly_metrics:
        return pd.DataFrame()

    years = sorted(yearly_metrics.keys())
    if len(years) < 2:
        return pd.DataFrame()

    rows = []
    for year in years:
        metrics = yearly_metrics[year]
        rows.append({
            "year": year,
            "commits": metrics.total_commits,
            "loc": getattr(metrics, "total_loc", 0),
        })

    df = pd.DataFrame(rows)

    # Calculate YoY growth
    df["commits_yoy_growth"] = df["commits"].pct_change() * 100
    df["loc_yoy_growth"] = df["loc"].pct_change() * 100

    return df


def print_yoy_comparison(yoy_df: pd.DataFrame):
    """Print year-over-year comparison."""
    if yoy_df.empty:
        console.print("[yellow]No multi-year data available for comparison[/yellow]")
        return

    table = Table(title="Year-over-Year Comparison")
    table.add_column("Year", style="cyan")
    table.add_column("Commits", style="green")
    table.add_column("Growth", style="yellow")
    table.add_column("LOC", style="blue")
    table.add_column("Growth", style="magenta")

    for _, row in yoy_df.iterrows():
        commits_growth = f"{row['commits_yoy_growth']:+.1f}%" if not pd.isna(row['commits_yoy_growth']) else "N/A"
        loc_growth = f"{row['loc_yoy_growth']:+.1f}%" if not pd.isna(row['loc_yoy_growth']) and row['loc'] > 0 else "N/A"

        table.add_row(
            str(int(row['year'])),
            f"{int(row['commits']):,}",
            commits_growth,
            f"{int(row['loc']):,}" if row['loc'] > 0 else "N/A",
            loc_growth,
        )

    console.print()
    console.print(table)
