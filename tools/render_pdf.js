// Render the handbook HTML to an A4 PDF with Chromium (Playwright). Usage: node render_pdf.js in.html out.pdf
const { chromium } = require('playwright');
const path = require('path');
(async () => {
  const [inp, out] = process.argv.slice(2);
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.goto('file://' + path.resolve(inp), { waitUntil: 'load', timeout: 300000 });
  await page.evaluate(() => document.fonts.ready);
  const foot = `<div style="width:100%;font-family:Inter,DejaVu Sans,sans-serif;font-size:7.5px;color:#6c757d;
    padding:0 16mm;display:flex;justify-content:space-between;">
    <span>VeriQ Handbook v5 · TELIPORT S4 Case 3 · labels: measured / target / starting parameter / illustrative / hypothesis</span>
    <span><span class="pageNumber"></span> / <span class="totalPages"></span></span></div>`;
  await page.pdf({
    path: out, format: 'A4', printBackground: true, displayHeaderFooter: true,
    headerTemplate: '<div></div>', footerTemplate: foot,
    margin: { top: '16mm', bottom: '16mm', left: '16mm', right: '16mm' },
    outline: true, tagged: true, timeout: 0,
  });
  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
