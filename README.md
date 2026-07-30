# star-history

English | [日本語](README_ja.md)

GitHub [restricted the stargazers API to owners/collaborators on 2026-06-30](https://github.blog/changelog/2026-06-30-upcoming-access-restrictions-to-public-api-endpoints-and-ui-views/), which broke the README-embedded charts from star-history.com. This repository is a replacement: it periodically generates star history charts for your own repositories via GitHub Actions and serves them as static SVGs.

- Fetches star history daily at 06:00 JST (cron) using the owner's fine-grained PAT
- Generates light/dark theme SVGs in `charts/` and commits them
- Each repository's README only references a fixed `raw.githubusercontent.com` URL, so no README updates are needed
- No dependencies (Python standard library only). Does not store any information about who starred — only timestamps

## Charts

<p align="center">
  <img alt="Star history of ryhara/hand_visibility_detector (light)" src="https://raw.githubusercontent.com/ryhara/star-history/main/charts/ryhara_hand_visibility_detector.svg" width="49%">
  <img alt="Star history of ryhara/hand_visibility_detector (dark)" src="https://raw.githubusercontent.com/ryhara/star-history/main/charts/ryhara_hand_visibility_detector_dark.svg" width="49%">
</p>

<p align="center">
  <img alt="Star history of ryhara/hamer-mini (light)" src="https://raw.githubusercontent.com/ryhara/star-history/main/charts/ryhara_hamer-mini.svg" width="49%">
  <img alt="Star history of ryhara/hamer-mini (dark)" src="https://raw.githubusercontent.com/ryhara/star-history/main/charts/ryhara_hamer-mini_dark.svg" width="49%">
</p>

## Usage

### 1. Register a token

Create a [fine-grained PAT](https://github.com/settings/personal-access-tokens) with the following settings:

- **Repository access**: "Only select repositories" and select all target repositories (a single token can cover multiple repositories)
- **Repository permissions**:
  - **Metadata: Read-only** (granted automatically when repositories are selected)
  - **Contents: Read and write** ← Required. Since the 2026-06 restriction, the stargazers API requires `metadata=read; contents=write` (verifiable via the `x-accepted-github-permissions` header on a 403 response). The write permission is used as proof of being an owner/collaborator, so Read-only is not sufficient

Register the created token as the Secret `STAR_HISTORY_TOKEN` in this repository:

```bash
gh secret set STAR_HISTORY_TOKEN -R ryhara/star-history
```

To add more target repositories later, just add them to the token's Repository access on its Edit page (the token value doesn't change, so no Secret update is needed).

### 2. Add target repositories

List one repository per line in `repos.txt`. Charts are regenerated immediately on push.

### 3. Embed in a README

```html
<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/ryhara/star-history/main/charts/{owner}_{repo}_dark.svg">
    <img alt="Star History" src="https://raw.githubusercontent.com/ryhara/star-history/main/charts/{owner}_{repo}.svg">
  </picture>
</p>
```

### Manual / local runs

```bash
gh workflow run update.yml -R ryhara/star-history   # manual trigger
GH_TOKEN=$(gh auth token) python3 generate_star_history.py  # local
```

## Notes

- Only the star **count** over time is published. Who starred (the data GitHub restricted) is neither stored nor published
- Fine-grained PATs have an expiration date, so update the Secret when the token expires
- Scheduled workflows are automatically disabled after 60 days of repository inactivity (in practice this is not an issue here, since chart update commits keep the repository active)
