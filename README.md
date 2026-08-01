# Automated Research Paper Podcast Generator

Daily Serverless Research Paper Discovery and Podcast Synthesis using Semantic Scholar API and Google NotebookLM.

[![License: MIT](https://img.shields.org/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.org/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![GitHub Actions](https://img.shields.org/badge/CI-GitHub--Actions-blue)](https://github.com/lqSky7/PpodcastDaily/actions)

An automated, serverless Python pipeline that discovers high-impact research papers using the **Semantic Scholar Recommendations API**, ingests them into **Google NotebookLM (`notebooklm-py`)**, triggers long-form structured audio overview podcast synthesis, and runs headlessly on GitHub Actions.

---

## Overview

This project automates daily research paper discovery and audio overview creation. It evaluates research paper candidates based on user-defined seed paper embeddings and credibility thresholds, filters out uncited or irrelevant works, and instructs Google NotebookLM AI hosts to generate structured technical podcast episodes.

---

## Key Features

- **Semantic Scholar Recommendation Engine**: Uses seed paper embeddings (Bayesian Optimization, Hyperparameter Tuning, Cognitive Neuroscience, Sleep and Memory) to discover relevant, open-access research papers.
- **Credibility and Citation Filtering**: Enforces minimum citation thresholds and recent publication filters to exclude low-quality or zero-citation papers.
- **Dynamic Non-Repeating Pipeline**: Shuffles seed subsets and maintains persistent recommendation history to guarantee new, distinct paper recommendations on every run.
- **Structured Podcast Prompting**: Directs NotebookLM hosts to follow a strict format: Abstract explanation, Conclusion and implications, and key Methodology details.
- **NotebookLM Source Discovery Fallback**: If direct paper URL ingestion fails (or DOI links are likely to be rate-limited), NotebookLM web research is used to discover and import alternative sources automatically.
- **Automated Local Cookie Sync**: Includes a native macOS CLI utility (`sync_auth.py`) that extracts and decrypts local Chromium/Dia browser session cookies via macOS Keychain and updates GitHub Actions Secrets automatically.
- **Serverless & Cost Efficient**: Executes on GitHub Actions in fire-and-forget mode, triggering cloud audio rendering in seconds without wasting runner compute.

---

## Repository Structure

```text
├── config.json                            # Seed papers, topics, minimum citations, and podcast prompt
├── paper_recommender.py                   # Semantic Scholar paper discovery and filtering engine
├── podcast_generator.py                   # NotebookLM ingestion and audio generation runner
├── sync_auth.py                           # Native macOS browser cookie extraction & GitHub secret sync
├── requirements.txt                       # Python dependencies
└── .github/workflows/paper_podcast_cron.yml  # GitHub Actions cron workflow (Daily 8:00 AM IST)
```

---

## System Architecture

```text
[ Seed Papers / Topics ]
           │
           ▼
[ Semantic Scholar API ] ──(Filters: Open Access PDF + Min Citations)──► [ Target Paper ]
                                                                               │
                                                                               ▼
[ GitHub Actions / Cron ] ──(Restores NOTEBOOKLM_STORAGE_STATE)────────► [ Google NotebookLM ]
                                                                               │
                                                                               ▼
                                                                 [ Audio Overview Podcast ]
```

---

## Quick Start Guide

### 1. Prerequisites

- Python 3.11 or higher
- GitHub CLI (`gh`) authenticated via `gh auth login`

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Local Authentication Sync

Run the local authentication utility to extract your session cookies and sync them to your GitHub repository secret (`NOTEBOOKLM_STORAGE_STATE`):

```bash
python3 sync_auth.py
```

### 4. Scheduled and Manual Execution

- **Scheduled**: Runs automatically every day at 8:00 AM IST (`02:30 UTC`).
- **Manual**: Trigger on-demand via the GitHub Actions UI under `Actions > Generate Research Paper Podcast > Run workflow`.

---

## Configuration

Edit `config.json` to customize your seed papers, topic preferences, and citation filters:

```json
{
  "seed_papers": [
    {
      "title": "Practical Bayesian Optimization of Machine Learning Algorithms",
      "id": "ARXIV:1206.2944"
    },
    {
      "title": "Sleep-dependent learning: a nap to remember",
      "id": "DOI:10.1038/nn1063"
    }
  ],
  "min_citations": 5,
  "podcast_format": "deep-dive"
}
```

---

## License

This project is open-source software licensed under the MIT License.
