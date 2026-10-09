const { devices } = require("@playwright/test");
module.exports = {
  testDir: "./frontend/manual-workspace-browser",
  timeout: 30000,
  fullyParallel: false,
  workers: 1,
  retries: 0,
  outputDir: "test-results/manual-workspace",
  use: {
    baseURL: "http://127.0.0.1:8767",
    headless: true,
    trace: "off",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: "python -m http.server 8767 --bind 127.0.0.1 --directory frontend",
    url: "http://127.0.0.1:8767/manual-workspace.html",
    reuseExistingServer: false,
    timeout: 15000,
  },
};
