#!/bin/bash
# Create GitHub release draft with images

VERSION="v0.4.2"
TITLE="v0.4.2 - Developer Experience Update"
IMAGES_DIR="docs/images/release-notes"
ANNOUNCEMENT_FILE="${IMAGES_DIR}/v0.4.2-release-announcement.md"

# Check if release already exists
if gh release view ${VERSION} &>/dev/null; then
    echo "Release ${VERSION} already exists. Updating..."
    # Upload any missing images
    gh release upload ${VERSION} ${IMAGES_DIR}/*.png --clobber
    # Update the release notes
    gh release edit ${VERSION} --notes-file ${ANNOUNCEMENT_FILE}
else
    # Create draft release with images and announcement
    echo "Creating draft release ${VERSION}..."
    gh release create ${VERSION} \
      --title "${TITLE}" \
      --draft \
      --notes-file ${ANNOUNCEMENT_FILE} \
      ${IMAGES_DIR}/*.png
fi

echo "✅ Draft release ${VERSION} is ready!"
echo ""

# Ask if user wants to publish
read -p "Do you want to publish the release now? (y/N): " confirm
if [[ "$confirm" =~ ^[Yy]$ ]]; then
    echo "Publishing release..."
    gh release edit ${VERSION} --draft=false
    echo "✅ Release ${VERSION} published successfully!"
    echo "View it at: https://github.com/Aurite-ai/aurite-agents/releases/tag/${VERSION}"
else
    echo "Release draft is available at: https://github.com/Aurite-ai/aurite-agents/releases"
    echo "You can publish it later with: gh release edit ${VERSION} --draft=false"
fi
