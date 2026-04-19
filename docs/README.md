# Project site

This folder contains a simple project website for Disk Organiser. To publish this site on GitHub Pages:

1. Go to the repository Settings → Pages.
2. Set "Source" to "main" branch and select the "/docs" folder.
3. Save and wait a few minutes for the site to publish at https://krahd.github.io/disk_organiser/.

If you prefer to use a separate `gh-pages` branch, create and push that branch and set Pages source accordingly.

For local preview open `docs/index.html` in a browser.

Automated publishing

This repository includes a GitHub Actions workflow at .github/workflows/publish-docs.yml that can automatically publish the `docs/` folder to a `gh-pages` branch whenever commits are pushed to `main`. The workflow uses `peaceiris/actions-gh-pages` to push the built files to a `gh-pages` branch.

To use the automated workflow:

- Merge the workflow file to `main`.
- (Optional) In repository Settings → Pages set the source to `gh-pages` branch so GitHub Pages serves the `gh-pages` branch.

Demo

A static copy of the frontend is included under `docs/demo/` for a read-only preview of the UI. Note that interactive features that require the backend API will not function on the published site.

Access the demo at: https://krahd.github.io/disk_organiser/demo/

If you prefer to have Pages directly serve `/docs` from `main` (no deployment step), you can continue using the `main` branch `/docs` source in Pages settings instead of the `gh-pages` branch.

