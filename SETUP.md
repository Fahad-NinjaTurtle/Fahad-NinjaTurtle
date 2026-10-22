# Fahad's auto-updating light/dark profile README — setup

**Ready for:** `https://github.com/Fahad-NinjaTurtle`

The terminal is a **real SVG image** in two color variants. In `README.md`, GitHub's `<picture>` chooses the image based on the visitor's color preference. The job embeds your **real GitHub profile photo inside each SVG** after the first successful sync; no external image references are needed at display time.

## 1. Create the special profile repository

On GitHub create a new **public** repository named **exactly** `Fahad-NinjaTurtle` under the account `Fahad-NinjaTurtle` (it must match your username, including the dash). A README at the repository root will appear on your profile automatically.

If a repository with that name already exists, use it rather than creating a second one; keep any files you want to preserve.

## 2. Upload everything (keep folders intact)

Unzip the package, then put these files inside the **root** of that GitHub repository:

```
Fahad-NinjaTurtle/
├── README.md
├── SETUP.md
├── profile.json
├── assets/
│   ├── terminal-dark.svg
│   └── terminal-light.svg
├── data/
│   └── stats.json
├── scripts/
│   └── generate.py
└── .github/
    └── workflows/
        └── update-profile.yml
```

**Using Git (recommended for nested/hidden folders):** Open a terminal inside the unzipped folder and run:

```bash
git init
git add .
git commit -m "Add auto-updating terminal profile README"
git branch -M main
git remote add origin https://github.com/Fahad-NinjaTurtle/Fahad-NinjaTurtle.git
git push -u origin main
```

This assumes the new remote is empty and you have Git authentication set up. If the repository has existing files, clone it instead and copy the contents of this package into your clone, then `git add .`, `git commit`, `git push`.

**Using GitHub website:** In the repository use **Add file > Upload files** and upload files preserving the path layout, including `.github/workflows/update-profile.yml`. Uploading just the SVGs and README won't enable refreshes.

## 3. Sync the REAL avatar and GitHub statistics

Open your repository's **Actions** tab. If prompted, enable workflows. Pick the workflow **Update terminal profile & real GitHub stats** and click **Run workflow** on the `main` branch.

The workflow automatically:

1. Reads your public profile data from GitHub's REST API.
2. Fetches the current GitHub avatar and **base64-embeds it into both SVG images**.
3. Retrieves your **public repo count**, **stars received by your public repos**, and top **primary programming languages** among your repos.
4. Retrieves your **commits contributed** and **PRs opened** in the past year via GitHub's GraphQL contributions data. PRs replace the sample card's follower count.
5. Commits the refreshed SVGs and data back to the repository.

It refreshes about **every six hours** while GitHub Actions scheduling is active; GitHub may delay or temporarily disable scheduled workflows for inactive repositories. You can always run it manually. If commits cannot be pushed, make sure the workflow is allowed **write access to repository contents** under **Settings > Actions > General > Workflow permissions** (organization policies may restrict this).

`secrets.GITHUB_TOKEN` is automatically provided by GitHub Actions; **no personal access token or third-party paid service** is required. If the GraphQL contribution API rejects the Actions token, the generator shows `—` for data it cannot verify rather than inventing values; check the workflow logs.

The avatar initially uses a vector turtle placeholder because a direct photo download isn't possible in this offline package; it will be replaced with the **actual GitHub profile picture** at the first successful workflow run.

## 4. Customize text and preview both themes

Edit `profile.json` for name, portfolio, organization, focus, and other textual fields. This file includes only publicly listed profile information. To regenerate the SVGs locally with the last saved stats (no API access required):

```bash
python scripts/generate.py --offline
```

To also refresh data locally, authenticate first with a `GITHUB_TOKEN` in your environment, then run:

```bash
python scripts/generate.py
```

For quick testing open `assets/terminal-dark.svg` and `assets/terminal-light.svg` in a web browser. On your GitHub profile, switch the GitHub **Appearance** setting or your preferred light/dark appearance and confirm the `<picture>` variant switches.

## Statistics definitions

- **Public repos:** `public_repos` from your public GitHub user API.
- **Stars earned:** sum of `stargazers_count` on your owned public repositories, **not** the number of repos you've starred.
- **Commits / 365d:** GitHub GraphQL `contributionsCollection.totalCommitContributions`, i.e., commits included in your profile contribution counts for the preceding year, **not** your lifetime commit count.
- **PRs / 365d:** GitHub GraphQL `contributionsCollection.totalPullRequestContributions`, covering opened pull requests counted in the preceding year.
- **Languages:** most frequent *primary repository languages* from GitHub's API, not byte-weighted language share.

Only **public stats available to the workflow** are expected. Contribution totals can depend on GitHub's visibility rules for private contributions, GitHub's contribution eligibility criteria, and API permissions. Unknown values are shown as `—`.

## Troubleshooting

- **Avatar still an illustration / some stats `—`?** Run the workflow at least once; check the Actions log for any API failures.
- **Images look stale?** GitHub may cache SVG files for some time. Try a hard refresh or check the latest file commit first.
- **Neither SVG appears?** Confirm image files are under `assets/` and `README.md` is in the root of the public profile repository.
- **Workflow not shown?** Ensure `.github/workflows/update-profile.yml` was uploaded on the default branch and Actions is enabled.
- **Wrong theme?** Make sure `README.md` contains the full `<picture>` block. Browsers and GitHub versions use color-scheme preferences differently; inspect your Appearance setting.
