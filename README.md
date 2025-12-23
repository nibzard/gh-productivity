# gh-productivity

GitHub productivity analysis tool with AI collaboration detection.

## Features

- **Activity Analysis**: Track commits, PRs, and code changes across all repos
- **AI Detection**: Automatically detect AI-assisted commits (Claude, Copilot, Codex, Cursor, Aider, Cline)
- **Visualizations**: Generate interactive HTML charts with Plotly
- **Multi-language**: Analyze projects in any programming language
- **2025 Ready**: Pre-configured for year-based analysis

## AI Detection Patterns

Detects commits from:
- **Claude** (`Co-Authored-By: Claude`, `claude@anthropic.com`)
- **GitHub Copilot** (`copilot@github.com`, `Co-Authored-By: GitHub Copilot`)
- **Cursor** (`Co-Authored-By: Cursor`)
- **Aider** (`Co-Authored-By: Aider`)
- **Cline** (`Co-Authored-By: Cline`)
- **Codex** (`codex@openai.com`)
- And more via keyword detection

## Installation

```bash
# Clone the repo
git clone https://github.com/nibzard/gh-productivity.git
cd gh-productivity

# Install dependencies
pip install click pandas numpy requests matplotlib plotly pyarrow python-dateutil tqdm rich

# Or install the package
pip install -e .
```

## Quick Start

```bash
# 1. Export your repos to JSON
gh api "user/repos?type=all&per_page=100" --paginate --jq '.' > repos.json

# 2. Run full analysis
PYTHONPATH=. python3 -m gh_productivity.cli run --year 2025 --repos repos.json
```

## CLI Usage

```bash
# Step-by-step
gh-productivity collect --year 2025 --repos repos.json
gh-productivity process
gh-productivity analyze
gh-productivity visualize

# Or run all at once
gh-productivity run --year 2025 --repos repos.json
```

## Requirements

- Python 3.11+
- GitHub CLI (`gh`) installed and authenticated
- GitHub Personal Access Token for API access

## Output

```
data/
├── raw/              # Raw API responses
└── processed/        # Parquet files
    ├── commits.parquet
    ├── prs.parquet
    └── repos.parquet

plots/                # Interactive HTML charts
    ├── activity_heatmap.html
    ├── ai_vs_solo.html
    ├── ai_by_repo.html
    ├── ai_agents.html
    └── ...
```

## Example Output

```
      2025 Productivity Summary
┏━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┓
┃ Metric              ┃ Value        ┃
┡━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━┩
│ Total Commits       │ 7761         │
│ Active Repos        │ 158          │
│ Coding Days         │ 357          │
│ AI-Assisted Commits │ 2087 (26.9%) │
│ Primary AI Agent    │ claude       │
└─────────────────────┴──────────────┘
```

## License

MIT

## Author

@nibzard
