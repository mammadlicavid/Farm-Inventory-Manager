const fs = require('fs/promises');
const path = require('path');
const puppeteer = require('puppeteer');

const projectRoot = path.resolve(__dirname, '..');
const screenshotDir = process.argv[2]
  ? path.resolve(process.cwd(), process.argv[2])
  : path.join(projectRoot, 'artifacts', 'responsive');

async function capturePage(page, options) {
  const { url, width, height, filename, waitForSelector } = options;

  await page.setViewport({ width, height });
  await page.goto(url, { waitUntil: 'networkidle0' });

  if (waitForSelector) {
    await page.waitForSelector(waitForSelector);
  }

  await page.screenshot({
    path: path.join(screenshotDir, filename),
    fullPage: true,
  });
}

async function run() {
  await fs.mkdir(screenshotDir, { recursive: true });

  const browser = await puppeteer.launch({ headless: true });

  try {
    const desktopPage = await browser.newPage();
    await capturePage(desktopPage, {
      url: 'http://127.0.0.1:8000/dashboard/',
      width: 1280,
      height: 800,
      filename: 'desktop_dashboard.png',
      waitForSelector: '.categories-grid',
    });

    await capturePage(desktopPage, {
      url: 'http://127.0.0.1:8000/expenses/',
      width: 1280,
      height: 800,
      filename: 'desktop_expenses.png',
      waitForSelector: '.desktop-form-grid',
    });

    const mobilePage = await browser.newPage();
    await capturePage(mobilePage, {
      url: 'http://127.0.0.1:8000/expenses/',
      width: 390,
      height: 844,
      filename: 'mobile_expenses.png',
      waitForSelector: '.page-title',
    });

    console.log(`Responsive screenshots saved to ${screenshotDir}`);
  } finally {
    await browser.close();
  }
}

run().catch((error) => {
  console.error(error);
  process.exit(1);
});
