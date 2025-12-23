"""Generate visualizations."""

import json
from pathlib import Path
from datetime import datetime

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from rich.console import Console

console = Console()


# Set style
plt.style.use("dark_background")
plt.rcParams["figure.facecolor"] = "#1a1a2e"
plt.rcParams["axes.facecolor"] = "#16213e"


def plot_activity_heatmap(commits_df: pd.DataFrame, output_path: Path):
    """Plot GitHub-style activity heatmap."""
    if commits_df.empty:
        return

    df = commits_df.copy()
    df["date_only"] = pd.to_datetime(df["date"]).dt.date
    daily_counts = df.groupby("date_only").size().reset_index(name="count")
    daily_counts["date_only"] = pd.to_datetime(daily_counts["date_only"])

    fig = go.Figure(data=go.Scatter(
        x=daily_counts["date_only"],
        y=daily_counts["count"],
        mode="markers",
        marker=dict(
            size=10,
            color=daily_counts["count"],
            colorscale="Viridis",
            showscale=True,
            colorbar=dict(title="Commits"),
        ),
        hovertemplate="%{x}<br>Commits: %{y}<extra></extra>",
    ))

    fig.update_layout(
        title="Daily Commit Activity - 2025",
        xaxis_title="Date",
        yaxis_title="Commits",
        height=400,
        template="plotly_dark",
    )

    fig.write_html(output_path / "activity_heatmap.html")
    console.print(f"[green]✓[/green] Saved activity heatmap")


def plot_language_breakdown(repos_df: pd.DataFrame, output_path: Path):
    """Plot language distribution pie chart."""
    if repos_df.empty:
        return

    lang_stats = repos_df.groupby("language")["net_lines"].sum().sort_values(ascending=False)
    lang_stats = lang_stats[lang_stats > 0]

    fig = go.Figure(data=go.Pie(
        labels=lang_stats.index,
        values=lang_stats.values,
        hole=0.4,
    ))

    fig.update_layout(
        title="Language Distribution (by net lines)",
        template="plotly_dark",
    )

    fig.write_html(output_path / "language_breakdown.html")
    console.print(f"[green]✓[/green] Saved language breakdown")


def plot_commit_frequency(commits_df: pd.DataFrame, output_path: Path):
    """Plot commit frequency over time."""
    if commits_df.empty:
        return

    df = commits_df.copy()
    df["week"] = pd.to_datetime(df["date"]).dt.to_period("W")
    weekly_counts = df.groupby("week").size().reset_index(name="count")
    weekly_counts["week"] = weekly_counts["week"].dt.start_time

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=weekly_counts["week"],
        y=weekly_counts["count"],
        mode="lines+markers",
        name="Weekly Commits",
        line=dict(color="#00d4aa", width=2),
    ))

    fig.update_layout(
        title="Weekly Commit Frequency - 2025",
        xaxis_title="Week",
        yaxis_title="Commits",
        template="plotly_dark",
        height=400,
    )

    fig.write_html(output_path / "commit_frequency.html")
    console.print(f"[green]✓[/green] Saved commit frequency")


def plot_ai_vs_solo(commits_df: pd.DataFrame, output_path: Path):
    """Plot AI-assisted vs solo commits over time."""
    if commits_df.empty:
        return

    df = commits_df.copy()
    df["week"] = pd.to_datetime(df["date"]).dt.to_period("W")

    weekly_ai = df.groupby(["week", "is_ai_assisted"]).size().reset_index(name="count")
    weekly_ai["week"] = weekly_ai["week"].dt.start_time

    solo = weekly_ai[~weekly_ai["is_ai_assisted"]]
    ai = weekly_ai[weekly_ai["is_ai_assisted"]]

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=solo["week"],
        y=solo["count"],
        mode="lines+markers",
        name="Solo",
        stackgroup="one",
        line=dict(color="#00d4aa"),
    ))

    fig.add_trace(go.Scatter(
        x=ai["week"],
        y=ai["count"],
        mode="lines+markers",
        name="AI-Assisted",
        stackgroup="one",
        line=dict(color="#ff6b6b"),
    ))

    fig.update_layout(
        title="Solo vs AI-Assisted Commits - 2025",
        xaxis_title="Week",
        yaxis_title="Commits",
        template="plotly_dark",
        height=400,
    )

    fig.write_html(output_path / "ai_vs_solo.html")
    console.print(f"[green]✓[/green] Saved AI vs solo chart")


def plot_ai_by_repo(repos_df: pd.DataFrame, output_path: Path):
    """Plot AI usage by repo (top 20)."""
    if repos_df.empty:
        return

    top_repos = repos_df.nlargest(20, "commits_2025").copy()
    top_repos["ai_ratio"] = top_repos["ai_commits"] / top_repos["commits_2025"].replace(0, 1)
    top_repos = top_repos.sort_values("ai_ratio", ascending=True)

    fig = go.Figure(data=go.Bar(
        x=top_repos["ai_ratio"],
        y=top_repos["full_name"],
        orientation="h",
        marker=dict(color="#ff6b6b"),
    ))

    fig.update_layout(
        title="AI Usage by Repo (Top 20) - % AI-Assisted Commits",
        xaxis_title="AI Ratio",
        yaxis_title="Repo",
        template="plotly_dark",
        height=600,
    )

    fig.write_html(output_path / "ai_by_repo.html")
    console.print(f"[green]✓[/green] Saved AI by repo chart")


def plot_ai_agent_distribution(commits_df: pd.DataFrame, output_path: Path):
    """Plot AI agent distribution pie chart."""
    if commits_df.empty:
        return

    ai_commits = commits_df[commits_df["is_ai_assisted"] == True]

    if ai_commits.empty:
        console.print("[yellow]No AI commits found[/yellow]")
        return

    agent_counts = ai_commits["ai_agent"].value_counts()

    fig = go.Figure(data=go.Pie(
        labels=agent_counts.index,
        values=agent_counts.values,
        hole=0.4,
    ))

    fig.update_layout(
        title="AI Agent Distribution",
        template="plotly_dark",
    )

    fig.write_html(output_path / "ai_agents.html")
    console.print(f"[green]✓[/green] Saved AI agent distribution")


def plot_repo_breakdown(repos_df: pd.DataFrame, output_path: Path):
    """Plot top repos by commits."""
    if repos_df.empty:
        return

    top_repos = repos_df.nlargest(20, "commits_2025").sort_values("commits_2025", ascending=True)

    fig = go.Figure(data=go.Bar(
        x=top_repos["commits_2025"],
        y=top_repos["full_name"],
        orientation="h",
        marker=dict(color="#00d4aa"),
    ))

    fig.update_layout(
        title="Top Repos by Commits - 2025",
        xaxis_title="Commits",
        yaxis_title="Repo",
        template="plotly_dark",
        height=600,
    )

    fig.write_html(output_path / "repo_breakdown.html")
    console.print(f"[green]✓[/green] Saved repo breakdown")


def plot_multi_year_trend(
    yearly_metrics: dict,
    output_path: Path,
):
    """Plot multi-year commits and LOC trends.

    Args:
        yearly_metrics: Dict mapping year -> ProductivityMetrics
        output_path: Directory to save plot
    """
    if not yearly_metrics:
        return

    years = sorted(yearly_metrics.keys())
    commits = [yearly_metrics[y].total_commits for y in years]
    loc = [yearly_metrics[y].code_loc for y in years]

    fig = go.Figure()

    # Commits line
    fig.add_trace(go.Scatter(
        x=years,
        y=commits,
        mode="lines+markers",
        name="Commits",
        line=dict(color="#00d4aa", width=3),
        marker=dict(size=8),
    ))

    # LOC line (on secondary y-axis)
    fig.add_trace(go.Scatter(
        x=years,
        y=loc,
        mode="lines+markers",
        name="Code Lines (LOC)",
        yaxis="y2",
        line=dict(color="#ff6b6b", width=3),
        marker=dict(size=8),
    ))

    fig.update_layout(
        title="Multi-Year Productivity Trend",
        xaxis_title="Year",
        yaxis_title="Commits",
        yaxis2=dict(
            title="Code Lines (LOC)",
            overlaying="y",
            side="right",
            showgrid=False,
        ),
        template="plotly_dark",
        height=450,
        hovermode="x unified",
    )

    fig.write_html(str(output_path / "multi_year_trend.html"))
    console.print(f"[green]✓[/green] Saved multi-year trend")


def plot_benchmark_comparison(
    metrics,
    benchmark,
    output_path: Path,
):
    """Plot user vs average developer benchmark.

    Args:
        metrics: ProductivityMetrics
        benchmark: BenchmarkResult
        output_path: Directory to save plot
    """
    categories = ["LOC (lines)", "Commits"]
    user_vals = [benchmark.user_loc, benchmark.user_commits]
    avg_vals = [AVERAGE_DEVELOPER["loc_per_year"], AVERAGE_DEVELOPER["commits_per_year"]]

    fig = go.Figure(data=[
        go.Bar(
            name="You",
            x=categories,
            y=user_vals,
            marker=dict(color="#00d4aa"),
        ),
        go.Bar(
            name="Average Developer",
            x=categories,
            y=avg_vals,
            marker=dict(color="#ff6b6b"),
        ),
    ])

    fig.update_layout(
        title=f"You vs Average Developer ({metrics.year})",
        yaxis_title="Count",
        template="plotly_dark",
        height=400,
        barmode="group",
    )

    fig.write_html(str(output_path / "benchmark_comparison.html"))
    console.print(f"[green]✓[/green] Saved benchmark comparison")


def plot_loc_by_language_trend(
    yearly_loc_data: dict,
    output_path: Path,
):
    """Plot LOC by language over time (stacked area).

    Args:
        yearly_loc_data: Dict mapping year -> LOC DataFrame
        output_path: Directory to save plot
    """
    if not yearly_loc_data:
        return

    years = sorted(yearly_loc_data.keys())

    # Aggregate languages by year
    lang_by_year = {}
    for year in years:
        loc_df = yearly_loc_data[year]
        if loc_df.empty:
            continue

        for _, row in loc_df[loc_df["scanned"]].iterrows():
            by_lang = json.loads(row["by_language"])
            for lang, loc in by_lang.items():
                lang_by_year[lang] = lang_by_year.get(lang, {})
                lang_by_year[lang][year] = lang_by_year[lang].get(year, 0) + loc

    if not lang_by_year:
        return

    # Create stacked area chart
    fig = go.Figure()

    for lang, year_data in lang_by_year.items():
        year_values = [year_data.get(y, 0) for y in years]
        fig.add_trace(go.Scatter(
            x=years,
            y=year_values,
            mode="lines",
            stackgroup="one",
            name=lang,
            fill="tozeroy",
        ))

    fig.update_layout(
        title="Code Lines by Language Over Time",
        xaxis_title="Year",
        yaxis_title="Code Lines",
        template="plotly_dark",
        height=500,
        hovermode="x unified",
    )

    fig.write_html(str(output_path / "loc_by_language_trend.html"))
    console.print(f"[green]✓[/green] Saved LOC by language trend")


def plot_percentile_radar(
    benchmark,
    output_path: Path,
):
    """Plot percentile rankings as radar chart.

    Args:
        benchmark: BenchmarkResult
        output_path: Directory to save plot
    """
    # Calculate percentile scores (0-1 scale, capped at 1)
    loc_pct = min(benchmark.loc_vs_avg_pct, 3.0) / 3.0
    commits_pct = min(benchmark.commits_vs_avg_pct, 3.0) / 3.0

    # Tier scores (Below Average=0.25, Average=0.5, Top 10%=0.75, Top 1%=1.0)
    tier_scores = {
        "Below Average": 0.25,
        "Average": 0.5,
        "Top 10%": 0.75,
        "Top 1%": 1.0,
    }

    loc_tier_score = tier_scores.get(benchmark.loc_tier, 0.5)
    commits_tier_score = tier_scores.get(benchmark.commits_tier, 0.5)
    overall_tier_score = tier_scores.get(benchmark.overall_tier, 0.5)

    categories = ["LOC", "Commits", "Overall"]

    fig = go.Figure(data=go.Scatterpolar(
        r=[loc_pct, commits_pct, overall_tier_score],
        theta=categories,
        fill="toself",
        marker=dict(color="#00d4aa", size=0.1),
    ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 1],
            )),
        title="Percentile Rankings (Normalized)",
        template="plotly_dark",
        height=400,
    )

    fig.write_html(str(output_path / "percentile_radar.html"))
    console.print(f"[green]✓[/green] Saved percentile radar")


# Import for benchmark comparison
from .benchmarks import AVERAGE_DEVELOPER


def generate_all_visualizations(
    commits_df: pd.DataFrame,
    prs_df: pd.DataFrame,
    repos_df: pd.DataFrame,
    output_dir: Path,
    yearly_metrics: dict | None = None,
    benchmark = None,
    yearly_loc_data: dict | None = None,
):
    """Generate all visualizations.

    Args:
        commits_df: Commits DataFrame
        prs_df: Pull requests DataFrame
        repos_df: Repos DataFrame
        output_dir: Directory to save plots
        yearly_metrics: Optional dict mapping year -> ProductivityMetrics
        benchmark: Optional BenchmarkResult for comparison charts
        yearly_loc_data: Optional dict mapping year -> LOC DataFrame
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    console.print("\n[cyan]Generating visualizations...[/cyan]")

    plot_activity_heatmap(commits_df, output_dir)
    plot_language_breakdown(repos_df, output_dir)
    plot_commit_frequency(commits_df, output_dir)
    plot_ai_vs_solo(commits_df, output_dir)
    plot_ai_by_repo(repos_df, output_dir)
    plot_ai_agent_distribution(commits_df, output_dir)
    plot_repo_breakdown(repos_df, output_dir)

    # New visualizations (conditional)
    if yearly_metrics:
        plot_multi_year_trend(yearly_metrics, output_dir)

    if benchmark and benchmark.user_loc > 0:
        from .analyze import calculate_metrics
        # Create a metrics object for the plot
        metrics = type('Metrics', (), {
            'year': list(yearly_metrics.keys())[0] if yearly_metrics else 2025
        })()
        plot_benchmark_comparison(metrics, benchmark, output_dir)
        plot_percentile_radar(benchmark, output_dir)

    if yearly_loc_data:
        plot_loc_by_language_trend(yearly_loc_data, output_dir)

    console.print(f"\n[green]✓ All visualizations saved to {output_dir}[/green]")
