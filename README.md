# Company Scout

Register of target companies for the job search. The job search tool
(job-shortlist) reads `docs/companies.json` and searches every company that is
not paused for open positions.

## What the register holds per company
- Rating A/B/C, status (watching / applied / paused)
- Main segment and secondary segments, segment detail, country, headquarters, ownership
- Description and why it fits
- Key figures: revenue, operating profit, net profit, employees, net debt, equity ratio,
  total assets, market cap (with date)
- Careers page and job system (detected automatically)
- Contacts (name, role, email, phone) and a comment – **encrypted**
- Sources for the figures

## Privacy
The repository is public (needed for free GitHub Pages). Contacts and comments are
encrypted in your browser (AES-256-GCM, key derived from your passphrase with
PBKDF2, 310,000 rounds) before they are saved. The repository only ever contains
the encrypted text. Without the passphrase they cannot be read – also not by you,
so keep the passphrase safe.

All other fields (company data, rating, status, fit) are public.

## Setup
1. Create a **public** repository `company-scout` and upload all files, keeping the
   `.github` folder.
2. Settings → Actions → General → Workflow permissions → **Read and write permissions**.
3. Settings → Pages → Deploy from a branch → `main`, folder `/docs`.
4. Create a fine-grained token with Contents: Read and write for this repository
   (or add this repository to your existing job-shortlist token).
5. Open the page, click **GitHub access**, enter the repository and token.
6. Click **Unlock contacts** to set your passphrase.

## How changes flow
- Saving on the page writes `docs/companies.json` directly to the repository.
- That starts the workflow *Maintain job sources*: it detects the job system for
  companies that have none (from the careers page, or by name) and writes it back.
- Every Monday the workflow re-checks all job sources and marks failures.

## Files
- `docs/index.html` – the register page
- `docs/companies.json` – the data
- `scout/` – job-source detection (`python -m scout.run [--check]`)
- `tests/` – offline tests
