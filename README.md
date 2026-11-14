# Godot Docker image

Small Ubuntu-based images with the standard Godot editor and matching export
templates, published to `ghcr.io/bdrelling/godot` for `linux/amd64` and
`linux/arm64`. This is a binary distribution image, not a custom engine build.

## Recommendation

Keep this image for the existing container workflow. Its useful differences are
both Linux architectures, a small dependency set, and export templates shared
through `/usr/local/share/godot/export_templates`. Root and users created with
`useradd -m` can find those templates via the existing home-directory symlinks.
An arbitrary mounted home directory still needs that symlink provisioned.

| Option | Best fit | Tradeoff for this repository |
| --- | --- | --- |
| This image | Existing containers and ARM64 hosts | We maintain a small wrapper around official binaries and templates. |
| [barichello/godot-ci](https://github.com/abarichello/godot-ci) | A ready-made CI/export environment including Android tooling | Its published tags inspected on 2026-11-14 list amd64; its Dockerfile defaults to the x86-64 binary and root-owned templates. It is not a verified replacement for our ARM64/user setup. |
| [chickensoft-games/setup-godot](https://github.com/chickensoft-games/setup-godot) | Jobs that just need Godot on a GitHub Actions runner | Installs/caches the editor and optional templates on Linux, macOS or Windows; it does not supply a reusable container. |

For new runner-only CI, prefer the setup action. For existing container consumers,
retain this image until their architecture and user/template requirements have
been tested against a replacement. Container publication does not roll out a
running homelab service; that consumer upgrade remains a separate change.

## Versions and use

`godot-versions.json` is the only version-default source. It lists the supported
stable Godot 4 releases, starting at `4.7-stable`; the numerically greatest entry
is the default. The initial update includes `4.7.1-stable` and `4.7.2-stable`.
The [official archive](https://godotengine.org/download/archive/) lists 4.7.2 as
the latest stable on 2026-11-14; 4.8 is still a prerelease.

After the publishing workflow succeeds:

```sh
docker pull ghcr.io/bdrelling/godot:4.7.2-stable
docker run --rm ghcr.io/bdrelling/godot:4.7.2-stable godot --version
```

Pin consumers to an exact version, preferably also its registry digest. Version
tags identify the engine release but may be rebuilt when this image changes;
digests identify immutable image contents. `latest` is a convenience alias for
the greatest catalog version and should not drive unattended game upgrades.
These are Docker image tags, not Git release tags.

## Weekly release updates

[Check stable Godot releases](.github/workflows/check-godot-releases.yml) runs
Mondays at **07:17 UTC** and supports manual dispatch. It queries the
[official build releases](https://github.com/godotengine/godot-builds/releases)
through GitHub's paginated API, excludes drafts/prereleases, and opens or updates
one PR on `automation/godot-stable`. Each new catalog entry gets links to its
official release notes, downloads and interactive changelog in the PR body.

Every missing stable 4.x version at or above the baseline is included, even if
several ship between checks or an older minor receives a late patch. Existing
versions are retained. Godot 3, prereleases and a future Godot 5 require an
explicit policy change. Both Linux binaries and the matching export-template
asset must exist; API errors or missing assets fail the check instead of
silently reporting that everything is up to date.

The workflow uses only `GITHUB_TOKEN`. In **Settings → Actions → General →
Workflow permissions**, enable **Allow GitHub Actions to create and approve
pull requests** (the workflow only creates PRs). Organization policy may control
this setting. No personal access token is required. The token's explicit
contents/PR/actions permissions are declared in the workflow.

GitHub's bot-token-created PR workflows may wait for approval instead of running
automatically, so the release check explicitly dispatches the build workflow on
the bot branch. Check
that branch's **Build and publish** run before merging. It validates both
architectures without pushing; main publishes after merge. The normal PR event
also builds human-created PRs. Failed checks appear in Actions; configure GitHub
Actions notifications to receive failure alerts.

GitHub schedules can be delayed and only run from the default branch; public
repository schedules can be disabled after 60 days without repository activity.
This is a weekly scheduled check, not an uptime guarantee. Check that the
schedule remains enabled when the repo is idle, or use an external scheduler
to dispatch it if strict monitoring is required. See
[GitHub's scheduled-workflow behavior](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule).

## Build and publication

[Build and publish](.github/workflows/deploy.yml) builds every catalog version
with per-version caches. Relevant changes to main publish exact multi-architecture
tags. Only after every build succeeds does a separate job promote `latest`.
Rebuilding an older version via manual dispatch never moves `latest` backwards.
Manual dispatch from a branch builds without publishing; publication requires
`main`. Ensure the repository has Actions write access to the existing `godot`
GHCR package. Cleanup preserves all `*-stable` tags and their multi-architecture
children, and only considers untagged images older than seven days.

Local maintenance requires Python 3, Make and Docker:

```sh
make info
make build                              # greatest catalog version
make build GODOT_VERSION=4.7.1-stable    # explicit upstream tag
make deploy                             # exact version only; CI manages latest
python3 -m unittest discover -s tests -v
python3 scripts/godot_versions.py update
```

Direct Docker builds must supply `--build-arg GODOT_VERSION=<release-tag>`.
The installers require the version argument so their defaults cannot drift.
