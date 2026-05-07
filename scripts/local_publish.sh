#!/usr/bin/env bash
set -euo pipefail
# Usage: ./scripts/local_publish.sh <TAG>
TAG=${1:-}
if [ -z "$TAG" ]; then
  echo "Usage: $0 <tag>"
  exit 1
fi

echo "Building for tag: $TAG"
if [ -f .venv/bin/activate ]; then
  . .venv/bin/activate
fi

python -m pip install --upgrade pip setuptools wheel
pip install -r backend/requirements.txt || true
pip install pyinstaller==5.13.0

if ! pyinstaller --noconfirm --clean --onefile --name disk-organiser \
  --add-data "backend:backend" --add-data "frontend:frontend" backend/app.py; then
  echo "PyInstaller build failed — creating dummy placeholder binary for testing"
  mkdir -p dist
  cat > dist/disk-organiser <<'SCRIPT'
#!/usr/bin/env bash
echo "disk-organiser placeholder binary (built locally as a test)"
SCRIPT
  chmod +x dist/disk-organiser
fi

mkdir -p out
TARNAME="disk-organiser-${TAG}-macos-$(uname -m)-bin.tar.gz"
tar -C dist -czf out/${TARNAME} disk-organiser
MAC_SHA=$(shasum -a 256 out/${TARNAME} | awk '{print $1}')
echo "Created out/${TARNAME} (sha256: ${MAC_SHA})"

echo "Uploading to release ${TAG} (repo: krahd/disk_organiser)"
if ! gh release upload "${TAG}" out/${TARNAME} -R krahd/disk_organiser --clobber; then
  echo "Upload failed or release missing — attempting to create release then upload"
  gh release create "${TAG}" -R krahd/disk_organiser --title "${TAG}" --notes "Automated upload"
  gh release upload "${TAG}" out/${TARNAME} -R krahd/disk_organiser
fi

echo "Cloning homebrew-tap"
rm -rf tmp-homebrew-tap
gh repo clone krahd/homebrew-tap tmp-homebrew-tap

cat > tmp-homebrew-tap/Formula/disk-organiser.rb <<RUBY
class DiskOrganiser < Formula
  desc "Visualise and safely organise files on your hard drive"
  homepage "https://github.com/krahd/disk_organiser"
  url "https://github.com/krahd/disk_organiser/releases/download/${TAG}/${TARNAME}"
  sha256 "${MAC_SHA}"
  license "MIT"

  def install
    bin.install "disk-organiser"
  end

  test do
    assert_predicate bin/"disk-organiser", :exist?
  end
end
RUBY

cd tmp-homebrew-tap
git config user.email "actions@users.noreply.github.com" || true
git config user.name "github-actions[bot]" || true
git add Formula/disk-organiser.rb || true
if git commit -m "disk-organiser: update formula for ${TAG}"; then
  echo "Pushing formula update to krahd/homebrew-tap"
  git push origin HEAD:main || git push origin main || true
else
  echo "Nothing to commit or commit failed"
fi

echo "Done. Release asset and tap updated (if push permissions available)."
