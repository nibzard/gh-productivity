"""Temporal productivity pattern analysis."""

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd
from rich.console import Console

console = Console()


@dataclass
class TemporalMetrics:
    """Temporal productivity patterns."""

    # Heatmap data
    hourly_heatmap: list[list[int]]  # 7 days x 24 hours
    peak_hours: list[tuple[int, int]]  # [(hour, count), ...]

    # Work/Life balance
    weekend_commit_ratio: float
    after_hours_percentage: float
    work_life_interpretation: str

    # Classification
    chronotype: str  # "early bird", "night owl", "mixed"

    # Session analysis
    session_count: int
    avg_session_duration_minutes: float
    commits_per_session: float

    # Streak analysis
    current_streak: int
    longest_streak: int
    longest_streak_dates: tuple[str, str]
    avg_gap_between_streaks: float


def analyze_time_patterns(commits_df: pd.DataFrame) -> TemporalMetrics:
    """Analyze temporal patterns in commit data.

    Args:
        commits_df: DataFrame with 'date' column (datetime)

    Returns:
        TemporalMetrics with all temporal statistics
    """
    if commits_df.empty:
        return TemporalMetrics(
            hourly_heatmap=[[0] * 24 for _ in range(7)],
            peak_hours=[],
            weekend_commit_ratio=0.0,
            after_hours_percentage=0.0,
            work_life_interpretation="No data",
            chronotype="mixed",
            session_count=0,
            avg_session_duration_minutes=0.0,
            commits_per_session=0.0,
            current_streak=0,
            longest_streak=0,
            longest_streak_dates=("", ""),
            avg_gap_between_streaks=0.0,
        )

    df = commits_df.copy()
    df["hour"] = df["date"].dt.hour
    df["day_of_week"] = df["date"].dt.dayofweek  # 0=Mon, 6=Sun
    df["date_only"] = df["date"].dt.date

    # Build heatmap (7 rows x 24 columns)
    heatmap = np.zeros((7, 24), dtype=int)
    for _, row in df.iterrows():
        heatmap[row["day_of_week"], row["hour"]] += 1

    # Find top 3 peak hours
    hourly_counts = df.groupby("hour").size()
    peak_hours = list(hourly_counts.nlargest(3).items())

    # Determine chronotype
    morning_commits = hourly_counts[6:12].sum()
    evening_commits = hourly_counts[18:24].sum() + hourly_counts[0:2].sum()
    chronotype = _classify_chronotype(morning_commits, evening_commits)

    # Calculate work/life metrics
    is_weekend = df["day_of_week"] >= 5
    weekend_ratio = is_weekend.sum() / len(df)

    is_weekday = ~is_weekend
    is_after_hours = (df["hour"] < 9) | (df["hour"] >= 18)
    weekday_after_hours = (is_weekday & is_after_hours).sum()
    after_hours_pct = weekday_after_hours / is_weekday.sum() if is_weekday.sum() > 0 else 0.0

    work_life_interpretation = _interpret_work_life(weekend_ratio, after_hours_pct)

    # Session analysis
    sessions = detect_sessions(df)
    session_count = len(sessions)
    if sessions:
        avg_duration = np.mean([s["duration"] for s in sessions])
        commits_per_session = np.mean([s["commits"] for s in sessions])
    else:
        avg_duration = 0.0
        commits_per_session = 0.0

    # Streak analysis
    streak_info = calculate_streak_detailed(df)

    return TemporalMetrics(
        hourly_heatmap=heatmap.tolist(),
        peak_hours=peak_hours,
        weekend_commit_ratio=weekend_ratio,
        after_hours_percentage=after_hours_pct,
        work_life_interpretation=work_life_interpretation,
        chronotype=chronotype,
        session_count=session_count,
        avg_session_duration_minutes=avg_duration,
        commits_per_session=commits_per_session,
        current_streak=streak_info["current"],
        longest_streak=streak_info["longest"],
        longest_streak_dates=streak_info["dates"],
        avg_gap_between_streaks=streak_info["avg_gap"],
    )


def detect_sessions(
    commits_df: pd.DataFrame,
    gap_threshold_minutes: int = 30,
) -> list[dict]:
    """Detect coding sessions based on commit gaps.

    A session is a sequence of commits where each consecutive commit
    is within gap_threshold_minutes of the previous one.

    Args:
        commits_df: DataFrame with 'date' column (datetime)
        gap_threshold_minutes: Max gap between commits in same session

    Returns:
        List of session dicts: {start, end, duration, commits}
    """
    if commits_df.empty:
        return []

    df = commits_df.sort_values("date").copy()
    sessions = []

    current_session_commits = [df.iloc[0]]

    for i in range(1, len(df)):
        prev_time = current_session_commits[-1]["date"]
        curr_time = df.iloc[i]["date"]
        gap_minutes = (curr_time - prev_time).total_seconds() / 60

        if gap_minutes <= gap_threshold_minutes:
            # Continue session
            current_session_commits.append(df.iloc[i])
        else:
            # End current session, start new one
            if len(current_session_commits) > 0:
                session_start = current_session_commits[0]["date"]
                session_end = current_session_commits[-1]["date"]
                sessions.append({
                    "start": session_start,
                    "end": session_end,
                    "duration": (session_end - session_start).total_seconds() / 60,
                    "commits": len(current_session_commits),
                })
            current_session_commits = [df.iloc[i]]

    # Don't forget last session
    if current_session_commits:
        session_start = current_session_commits[0]["date"]
        session_end = current_session_commits[-1]["date"]
        sessions.append({
            "start": session_start,
            "end": session_end,
            "duration": (session_end - session_start).total_seconds() / 60,
            "commits": len(current_session_commits),
        })

    return sessions


def calculate_work_life_ratio(commits_df: pd.DataFrame) -> dict:
    """Calculate work/life balance metrics.

    Args:
        commits_df: DataFrame with 'date' column (datetime)

    Returns:
        Dict with weekend_ratio, after_hours_pct, interpretation
    """
    if commits_df.empty:
        return {
            "weekend_ratio": 0.0,
            "after_hours_pct": 0.0,
            "interpretation": "No data"
        }

    df = commits_df.copy()
    df["day_of_week"] = df["date"].dt.dayofweek
    df["hour"] = df["date"].dt.hour

    # Weekend: Sat(5), Sun(6)
    is_weekend = df["day_of_week"] >= 5
    weekend_ratio = is_weekend.sum() / len(df)

    # After hours on weekdays: before 9am or after 6pm
    is_weekday = ~is_weekend
    is_after_hours = (df["hour"] < 9) | (df["hour"] >= 18)
    weekday_after_hours = (is_weekday & is_after_hours).sum()
    after_hours_pct = weekday_after_hours / is_weekday.sum() if is_weekday.sum() > 0 else 0.0

    interpretation = _interpret_work_life(weekend_ratio, after_hours_pct)

    return {
        "weekend_ratio": weekend_ratio,
        "after_hours_pct": after_hours_pct,
        "interpretation": interpretation,
    }


def _classify_chronotype(morning_commits: int, evening_commits: int) -> str:
    """Classify as early bird, night owl, or mixed."""
    if morning_commits == 0 and evening_commits == 0:
        return "mixed"

    total = morning_commits + evening_commits
    ratio = morning_commits / total

    if ratio > 0.6:
        return "early bird"
    elif ratio < 0.4:
        return "night owl"
    else:
        return "mixed"


def _interpret_work_life(weekend_ratio: float, after_hours_pct: float) -> str:
    """Generate human-readable work/life interpretation."""
    if weekend_ratio > 0.3 and after_hours_pct > 0.5:
        return "High weekend + after-hours activity"
    elif weekend_ratio > 0.3:
        return "Significant weekend work"
    elif after_hours_pct > 0.5:
        return "Heavy after-hours coding"
    elif weekend_ratio < 0.1 and after_hours_pct < 0.2:
        return "Good work/life separation"
    else:
        return "Moderate off-hours activity"


def calculate_streak_detailed(commits_df: pd.DataFrame) -> dict:
    """Calculate detailed streak metrics.

    Args:
        commits_df: DataFrame with 'date' column (datetime)

    Returns:
        Dict with current, longest, dates, avg_gap
    """
    df = commits_df.copy()
    df["date_only"] = df["date"].dt.date
    dates = sorted(df["date_only"].unique())

    if not dates:
        return {
            "current": 0,
            "longest": 0,
            "dates": ("", ""),
            "avg_gap": 0.0,
        }

    # Calculate current streak (from most recent date backwards)
    current = 1
    for i in range(len(dates) - 1, 0, -1):
        if (dates[i] - dates[i - 1]).days == 1:
            current += 1
        else:
            break

    # Calculate longest streak
    longest = 1
    current_streak_len = 1
    streak_start_idx = 0
    longest_start_idx = 0

    for i in range(1, len(dates)):
        if (dates[i] - dates[i - 1]).days == 1:
            current_streak_len += 1
            if current_streak_len > longest:
                longest = current_streak_len
                longest_start_idx = streak_start_idx
        else:
            streak_start_idx = i
            current_streak_len = 1

    if longest > 1:
        longest_start = dates[longest_start_idx]
        longest_end = dates[longest_start_idx + longest - 1]
        longest_dates = (str(longest_start), str(longest_end))
    else:
        longest_dates = ("", "")

    # Calculate average gap between streaks
    gaps = []
    for i in range(1, len(dates)):
        gap = (dates[i] - dates[i - 1]).days
        if gap > 1:
            gaps.append(gap)
    avg_gap = sum(gaps) / len(gaps) if gaps else 0.0

    return {
        "current": current,
        "longest": longest,
        "dates": longest_dates,
        "avg_gap": avg_gap,
    }
