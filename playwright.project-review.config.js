const { devices } = require('@playwright/test');

module.exports = {
  testDir: './frontend/project-review-browser',
  timeout: 30000,
  fullyParallel: false,
  workers: 1,
  retries: 0,
  outputDir: 'test-results/project-review',
  use: {
    baseURL: 'http://127.0.0.1:8765',
    headless: true,
    trace: 'off',
    screenshot: 'only-on-failure'
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: {
    command: 'python prototypes/drive_administration/demo_server.py --port 8765',
    url: 'http://127.0.0.1:8765',
    reuseExistingServer: false,
    timeout: 15000
  }
};
