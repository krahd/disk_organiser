// @ts-check
const { devices } = require('@playwright/test');

/** @type {import('@playwright/test').PlaywrightTestConfig} */
module.exports = {
  testDir: './frontend/visual',
  timeout: 30 * 1000,
  expect: {
    timeout: 5000
  },
  use: {
    headless: true,
    viewport: { width: 1024, height: 768 },
    ignoreHTTPSErrors: true
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chromium'] }
    }
  ]
};
