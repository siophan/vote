# Sourced by deploy.sh from the repository root. Releases come only from a clean checkout of
# origin/main: rsync --delete makes the server match whatever tree is being deployed.
git fetch -q origin main
if [ -n "$(git status --porcelain)" ]; then
  echo "the working tree has changes or untracked files; commit them to main first" >&2
  git status --short >&2
  exit 1
fi
if [ "$(git rev-parse HEAD)" != "$(git rev-parse origin/main)" ]; then
  echo "HEAD ($(git rev-parse --short HEAD)) is not origin/main ($(git rev-parse --short origin/main))." >&2
  echo "Merge into main, push it, then deploy from a checkout of origin/main." >&2
  exit 1
fi
