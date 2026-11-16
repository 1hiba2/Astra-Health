# Repository presentation and publication

Suggested GitHub description:

> Astronaut health monitoring research prototype with React, FastAPI, explainable time-series alerts and optional Gemini explanations.

Suggested topics:

`astronaut-health`, `nasa-space-apps`, `research-prototype`, `applied-ai`, `time-series`, `explainable-ai`, `gemini-api`, `react`, `typescript`, `fastapi`, `python`, `sqlite`, `full-stack`

Do not add topics implying clinical certification, trained predictive models or proven medical accuracy. Confirm the contributor-supplied competition wording against the official team submission before using it in applications. Choose a license jointly with the contributors; this change does not invent one.

## Review and publish

Changes are prepared on `docs/academic-portfolio`, based on `d5c6cc7`. Application source files and the existing frontend lockfile are unchanged. Review the README rendering (including Mermaid), screenshot contents, contributor names and AI limitations.

```bash
git switch docs/academic-portfolio
git diff d5c6cc7 --stat
git diff d5c6cc7 -- README.md docs .env.example .gitignore requirements.lock.txt .github/workflows/ci.yml
python -m pytest -q
npx tsc --noEmit
npm run build
git push -u origin docs/academic-portfolio
```

Then open a pull request against the repository's existing default branch, review the CI results and merge through GitHub when satisfied. No force push is needed. The prepared branch has not been pushed and no GitHub settings were changed by this task. Paste the suggested description and topics into the repository's About settings when ready.

If transferring via the supplied Git bundle, from an existing clone use `git fetch /path/to/astra-health-portfolio.bundle docs/academic-portfolio:docs/academic-portfolio`, then switch to the branch and review. A source ZIP is also provided for inspection; it excludes databases, local environments and build caches.
