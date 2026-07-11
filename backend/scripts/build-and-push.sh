#!/usr/bin/env bash
# Build the FDMS backend image with OCI labels + a versioned tag set, and
# (optionally) push it to Azure Container Registry.
#
# Usage:
#   ACR_NAME=fdmsacr ./scripts/build-and-push.sh            # build only
#   ACR_NAME=fdmsacr ./scripts/build-and-push.sh --push     # build + push
#
# Optional env: IMAGE_NAME (default: fdms-backend), VERSION (default: pyproject).
set -euo pipefail

# Always run from the backend directory (Docker build context).
cd "$(dirname "$0")/.."

ACR_NAME="${ACR_NAME:?Set ACR_NAME to your registry name, e.g. fdmsacr}"
IMAGE_NAME="${IMAGE_NAME:-fdms-backend}"
REGISTRY="${ACR_NAME}.azurecr.io"
REPO="${REGISTRY}/${IMAGE_NAME}"

# Version = source of truth in pyproject.toml (override with VERSION=...).
VERSION="${VERSION:-$(grep -m1 '^version' pyproject.toml | cut -d'"' -f2)}"
VCS_REF="$(git rev-parse --short HEAD 2>/dev/null || echo unknown)"
BUILD_DATE="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
MAJOR="${VERSION%%.*}"
MINOR="${VERSION%.*}"

# Tagging strategy: immutable, specific tags for deploys + moving convenience tags.
#   :<version>   e.g. 0.1.0   -> the exact release (use THIS in deployments)
#   :<major.minor> e.g. 0.1   -> latest patch of a minor line
#   :<major>     e.g. 0       -> latest minor of a major line
#   :sha-<ref>               -> immutable, build-provenance tag
#   :latest                 -> convenience only; never deploy from :latest
TAGS=(
  "${REPO}:${VERSION}"
  "${REPO}:${MINOR}"
  "${REPO}:${MAJOR}"
  "${REPO}:sha-${VCS_REF}"
  "${REPO}:latest"
)
TAG_ARGS=()
for t in "${TAGS[@]}"; do TAG_ARGS+=(-t "$t"); done

echo "Building ${REPO}"
echo "  version=${VERSION} revision=${VCS_REF} date=${BUILD_DATE}"
docker build \
  --platform linux/amd64 \
  --build-arg VERSION="${VERSION}" \
  --build-arg VCS_REF="${VCS_REF}" \
  --build-arg BUILD_DATE="${BUILD_DATE}" \
  "${TAG_ARGS[@]}" \
  .

echo "Built tags:"
printf '  %s\n' "${TAGS[@]}"

if [[ "${1:-}" == "--push" ]]; then
  echo "Logging in to ${REGISTRY} and pushing..."
  az acr login --name "${ACR_NAME}"
  for t in "${TAGS[@]}"; do docker push "$t"; done
  echo "Push complete."
else
  echo "Dry run (no push). Re-run with --push to publish to ACR."
fi
