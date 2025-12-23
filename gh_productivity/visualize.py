"""Generate visualizations."""

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


def generate_all_visualizations(
    commits_df: pd.DataFrame,
    prs_df: pd.DataFrame,
    repos_df: pd.DataFrame,
    output_dir: Path,
):
    """Generate all visualizations."""
    output_dir.mkdir(parents=True, exist_ok=True)

    console.print("\n[cyan]Generating visualizations...[/cyan]")

    plot_activity_heatmap(commits_df, output_dir)
    plot_language_breakdown(repos_df, output_dir)
    plot_commit_frequency(commits_df, output_dir)
    plot_ai_vs_solo(commits_df, output_dir)
    plot_ai_by_repo(repos_df, output_dir)
    plot_ai_agent_distribution(commits_df, output_dir)
    plot_repo_breakdown(repos_df, output_dir)

    console.print(f"\n[green]✓ All visualizations saved to {output_dir}[/green]")
