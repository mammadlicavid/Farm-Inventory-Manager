const puppeteer = require('puppeteer');
const path = require('path');

const baseDir = '/Users/muradbakirov/.gemini/antigravity/brain/05545778-74ee-4c3a-a780-60fb005e5c7a/';

async function run() {
    const browser = await puppeteer.launch();
    
    // 1. Desktop
    const desktopPage = await browser.newPage();
    await desktopPage.setViewport({ width: 1280, height: 800 });
    
    await desktopPage.goto('http://127.0.0.1:8000/dashboard/', {waitUntil: 'networkidle0'});
    await desktopPage.screenshot({ path: path.join(baseDir, 'desktop_dashboard_final.png'), fullPage: true });
    
    await desktopPage.goto('http://127.0.0.1:8000/expenses/', {waitUntil: 'networkidle0'});
    await desktopPage.screenshot({ path: path.join(baseDir, 'desktop_expenses_final.png'), fullPage: true });

    // 2. Mobile
    const mobilePage = await browser.newPage();
    await mobilePage.setViewport({ width: 390, height: 844 });
    
    await mobilePage.goto('http://127.0.0.1:8000/expenses/', {waitUntil: 'networkidle0'});
    await mobilePage.screenshot({ path: path.join(baseDir, 'mobile_expenses_final.png'), fullPage: true });

    await browser.close();
}

run();
