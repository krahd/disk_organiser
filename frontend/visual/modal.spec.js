const { test, expect } = require('@playwright/test');
const path = require('path');

test('preview modal visual snapshot', async ({ page }) => {
  const indexPath = path.resolve(__dirname, '..', 'index.html');
  const url = 'file://' + indexPath;
  await page.goto(url);
  // ensure DOMContentLoaded handlers run
  await page.waitForLoadState('domcontentloaded');

  // inject a preview object and call the window helper
  const preview = {
    op: { id: 'op-visual-1' },
    summary: { actions: 2, files: 2, bytes: 2048 },
    actions: [
      { action: 'move', src: '/tmp/a', dst: '/recycle/a', size: 1024 },
      { action: 'delete', src: '/tmp/b', dst: '', size: 1024 }
    ]
  };

  await page.evaluate((p) => {
    // call modal helper exposed on window
    if (window.openPreviewModal) window.openPreviewModal(p);
  }, preview);

  // wait a moment for DOM update
  await page.waitForTimeout(100);

  // ensure modal visible
  const modalVisible = await page.isVisible('#preview-modal:not(.hidden)');
  expect(modalVisible).toBe(true);

  // take screenshot of the modal region
  const modal = await page.$('#preview-modal .modal-content');
  expect(modal).not.toBeNull();
  await expect(modal).toHaveScreenshot('preview-modal.png');
});
