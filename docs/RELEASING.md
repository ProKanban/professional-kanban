# Releasing Professional Kanban

Releases are reproducible artifacts built by GitHub Actions from a signed semantic
version tag. Do not upload locally built archives to a public release.

## One-time owner controls

These settings require repository-owner access and cannot be enforced by a branch:

1. Create a repository ruleset for `refs/tags/v*` that restricts tag creation,
   update, and deletion to release maintainers.
2. Enable immutable GitHub Releases when that setting is available for the
   repository.
3. Require the `CI` workflow on the protected default branch.
4. Keep GitHub Actions restricted to allowed actions and full commit-SHA pins.
5. Configure the private vulnerability-reporting feature used by `SECURITY.md`.

`gh skill publish --dry-run` warns when no tag-protection ruleset exists. Treat that
warning as an owner action, not as a condition a pull request can silently fix.

## Prepare

1. Choose `vMAJOR.MINOR.PATCH` according to Semantic Versioning. Installation,
   archive-layout, input-parsing, minimum-Python, and forecast-semantic changes may
   be breaking even when the Python function API is unchanged.
2. Update the version in `.codex-plugin/plugin.json`,
   `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`,
   `skills/professional-kanban/SKILL.md`, and `CHANGELOG.md`.
3. Replace the changelog's release date and leave a fresh `[Unreleased]` section.
4. Confirm the README's install commands still carry no version pin, so they
   resolve to the release being made.

## Verify before tagging

Run from a clean checkout:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -v
uvx --from 'reuse[charset-normalizer]==6.2.0' reuse lint
gh skill publish --dry-run
claude plugin validate --strict .

first_dir="$(mktemp -d)"
second_dir="$(mktemp -d)"
python3 scripts/build_release.py --output "$first_dir" --version v1.1.0
python3 scripts/build_release.py --output "$second_dir" --version v1.1.0
cmp "$first_dir/professional-kanban.zip" "$second_dir/professional-kanban.zip"
cmp "$first_dir/professional-kanban.skill" "$second_dir/professional-kanban.skill"
cmp "$first_dir/SHA256SUMS" "$second_dir/SHA256SUMS"
```

Substitute the intended version. Confirm CI passes on the exact commit and the
working tree is clean.

## Sign and push the tag

Create an annotated, cryptographically signed tag and inspect it before pushing:

```bash
git tag -s -a v1.1.0 -m "Professional Kanban v1.1.0"
git tag --verify v1.1.0
git push origin v1.1.0
```

The tag-only release workflow requires a GitHub-verified signed annotated tag that
points directly to a commit on `main`, plus a successful `CI` push run for that
exact commit. Its read-only job verifies manifest/changelog agreement, reruns
tests, builds deterministic `.skill` and `.zip` archives, and writes
`SHA256SUMS`. A separate no-checkout job receives write/OIDC authority only after
that work succeeds, attests the transferred artifacts, and creates the GitHub
Release with those three files.
If the workflow fails, fix the release on a new commit and version; do not move a
published tag or replace assets on an immutable release.

## Post-release smoke test

1. Download all three assets from GitHub and verify `SHA256SUMS`.
2. Upload the `.skill` through ChatGPT's Skills page and run one positive and one
   negative trigger prompt from `evals/cases.json`.
3. Upload the `.zip` through Claude's Customize > Skills page and run the same
   smoke prompts.
4. Add the repository marketplace to a clean Claude Code profile, install the
   plugin, reload plugins, and run both sample calculations.
5. Install the tagged skill into a temporary Codex directory with `gh skill
   install`, then confirm the bundled scripts are present and runnable.
6. Refresh marketplace listings only after the release artifacts pass. OpenAI and
   Anthropic marketplace acceptance is external to the release workflow and must
   never be claimed before approval.

Record any release problem in the changelog and issue tracker. A statistical or
parsing defect warrants a patch release; do not repair only the README if published
calculation behavior is wrong.
