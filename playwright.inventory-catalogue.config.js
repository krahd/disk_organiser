const { devices } = require("@playwright/test");
module.exports = {
  testDir: "./frontend/inventory-catalogue-browser",
  timeout: 30000,
  fullyParallel: false,
  workers: 1,
  retries: 0,
  outputDir: "test-results/inventory-catalogue",
  use: {
    baseURL: "http://127.0.0.1:8768",
    headless: true,
    trace: "off",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: "python -m http.server 8768 --bind 127.0.0.1 --directory frontend",
    url: "http://127.0.0.1:8768/inventory-catalogue.html",
    reuseExistingServer: false,
    timeout: 15000,
  },
};
