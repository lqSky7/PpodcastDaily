# 🎙️ Serverless Research Paper Podcast Generator

An automated, serverless pipeline that uses **Semantic Scholar Recommendations API** to discover paper recommendations based on your seed preferences, uploads the paper to **Google NotebookLM (`notebooklm-py`)**, generates a long-form podcast (Abstract → Conclusion → Methodology), and runs automatically via **GitHub Actions**.

---

## 🌟 Key Features

1. **Semantic Scholar Paper Recommendation Engine**:
   - Uses your seed paper library (Bayesian Optimization, Hyperparameter Tuning, Cognitive Neuroscience, Sleep & Memory) to find relevant newly published research papers with open-access PDFs.
2. **NotebookLM Automated Podcasting**:
   - Ingests paper PDFs programmatically.
   - Instructs NotebookLM hosts to **strictly read & explain the Abstract**, then **read & explain the Conclusion**, and briefly cover **Methodology**.
3. **One-Click Local Secret Auto-Sync**:
   - Run `python sync_auth.py` on your PC. It logs into NotebookLM and automatically uploads your session credentials (`storage_state.json`) directly to your **GitHub Actions Secrets**. No manual copy-pasting required!
4. **Serverless Execution**:
   - Runs on a cron schedule or on-demand via GitHub Actions `workflow_dispatch`.

---

## 📁 Repository Structure

```text
├── config.json                            # Seed papers, topics & podcast prompt configuration
├── paper_recommender.py                   # Semantic Scholar API paper discovery engine
├── podcast_generator.py                   # NotebookLM ingestion & podcast creation runner
├── sync_auth.py                           # Local CLI utility to login & auto-sync credentials to GitHub
├── requirements.txt                       # Project Python dependencies
└── .github/workflows/paper_podcast_cron.yml  # GitHub Actions serverless cron workflow
```

---

## 🚀 Quick Start Guide

### 1. Local Setup

Install dependencies:
```bash
pip install -r requirements.txt
```

### 2. Login & Sync Credentials to GitHub

Make sure you have [GitHub CLI (`gh`)](https://cli.github.com/) installed and logged in (`gh auth login`).

Then simply run:
```bash
python sync_auth.py
```

This will:
1. Open a browser window to authenticate with your Google account for NotebookLM.
2. Save credentials to `~/.notebooklm/storage_state.json`.
3. Automatically upload the credentials to your repository secret named `NOTEBOOKLM_STORAGE_STATE`.

### 3. Test Paper Recommendations Locally

You can test paper recommendation discovery anytime:
```bash
python paper_recommender.py
```

### 4. Trigger Serverless Run on GitHub

1. Push this repository to GitHub.
2. Go to the **Actions** tab in your GitHub repository.
3. Select **Generate Research Paper Podcast** and click **Run workflow**.
4. Once completed, download your podcast from the **Artifacts** section!

---

## ⚙️ Customizing Seed Papers & Topics

Edit `config.json` to update your seed papers or topic preferences:

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
  ]
}
```

---

## 🔑 Session Expiration & Refreshing

Google session cookies eventually expire every few weeks/months. If a GitHub Action run fails due to authentication:
1. Open terminal on your local PC.
2. Run `python sync_auth.py --force-login`.
3. Your updated credentials will instantly sync to GitHub Secrets!
