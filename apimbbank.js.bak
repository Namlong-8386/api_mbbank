const http = require('http');
const https = require('https');
const puppeteer = require('puppeteer');

const PORT = 3020;
const TOKEN = '8a362fd013f7feef9be0decf93538979';
const CAPTCHA_API = 'https://thueapibank.vn/api/captcha';
const MBBANK_URL = 'https://online.mbbank.com.vn';

const CONFIG = {
    phone: 'tai khoan',
    password: 'pass',
    stk: 'so tai khoan',
};

let browser = null;
let page = null;
let loggedIn = false;
let lastRefresh = 0;
let lastHistoryData = null;
let lastHistoryTime = 0;
let loginInProgress = false;

function httpsPost(url, data) {
    return new Promise((resolve, reject) => {
        const body = JSON.stringify(data);
        const urlObj = new URL(url);
        const req = https.request({
            hostname: urlObj.hostname, port: 443, path: urlObj.pathname, method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(body) }
        }, res => {
            let d = '';
            res.on('data', c => d += c);
            res.on('end', () => { try { resolve(JSON.parse(d)); } catch(e) { resolve({ raw: d }); } });
        });
        req.on('error', reject);
        req.write(body);
        req.end();
    });
}

async function solveCaptcha(imgBase64) {
    const result = await httpsPost(CAPTCHA_API, { access_token: TOKEN, type: 'mbbank', img_base64: imgBase64 });
    return result?.captcha || result?.data?.captcha || null;
}

async function initBrowser() {
    if (browser && page) return;
    if (browser) { try { await browser.close(); } catch(e) {} }
    browser = await puppeteer.launch({
        headless: 'new',
        args: [
            '--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage',
            '--disable-gpu', '--disable-images', '--disable-extensions',
            '--disable-background-networking', '--disable-sync'
        ]
    });
    page = await browser.newPage();
    await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36');
    await page.setExtraHTTPHeaders({ 'Accept-Language': 'vi-VN,vi;q=0.9' });
    await page.setRequestInterception(true);
    page.on('request', req => {
        if (['image', 'stylesheet', 'font', 'media'].includes(req.resourceType())) req.abort();
        else req.continue();
    });
    browser.on('disconnected', () => { loggedIn = false; browser = null; page = null; });
}

async function getCaptchaBase64() {
    return await page.evaluate(() => {
        const imgs = document.querySelectorAll('img');
        for (const img of imgs) {
            if (img.src && img.src.startsWith('data:image/png;base64,')) return img.src.replace('data:image/png;base64,', '');
        }
        return null;
    });
}

async function login() {
    if (loginInProgress) return { success: false, message: 'Đang login...' };
    loginInProgress = true;
    try {
        await initBrowser();
        console.log('📱 Mở MBBank...');
        await page.goto(MBBANK_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
        await new Promise(r => setTimeout(r, 500));
        await page.type('#user-id', CONFIG.phone, { delay: 5 });
        await page.type('#new-password', CONFIG.password, { delay: 5 });
        const captchaBase64 = await getCaptchaBase64();
        if (!captchaBase64) throw new Error('Không tìm thấy captcha');
        console.log('🤖 Giải captcha...');
        const captchaText = await solveCaptcha(captchaBase64);
        if (!captchaText) throw new Error('Giải captcha thất bại');
        console.log('📝 Captcha:', captchaText);
        const captchaInput = await page.$('input[placeholder*="MÃ KIỂM TRA"]');
        if (captchaInput) { await captchaInput.click({ clickCount: 3 }); await captchaInput.type(captchaText, { delay: 5 }); }
        await page.click('button.btnma');
        await new Promise(r => setTimeout(r, 1000));
        const text = await page.evaluate(() => document.body.innerText);
        if (text.includes('captcha không chính xác')) throw new Error('Sai captcha');
        if (text.includes('sai') || text.includes('incorrect') || text.includes('GW')) throw new Error('Sai thông tin');
        loggedIn = true;
        lastRefresh = Date.now();
        console.log('✅ Login thành công!');
        return { success: true };
    } catch(e) {
        console.log('❌ Login failed:', e.message);
        throw e;
    } finally {
        loginInProgress = false;
    }
}

async function getHistory() {
    if (!loggedIn || !page) throw new Error('Chưa login');
    try {
        await page.goto(`${MBBANK_URL}/information-account/source-account`, { waitUntil: 'domcontentloaded', timeout: 30000 });
        await new Promise(r => setTimeout(r, 1500));
        const url = page.url();
        if (url.includes('login')) { loggedIn = false; throw new Error('Session hết hạn'); }
        await page.evaluate(() => {
            const btns = document.querySelectorAll('button, a');
            for (const btn of btns) { if (btn.textContent?.includes('Truy vấn')) { btn.click(); return; } }
        });
        await new Promise(r => setTimeout(r, 2000));
        const { items, balance } = await page.evaluate(() => {
            const items = [];
            document.querySelectorAll('table tbody tr').forEach(row => {
                const cells = row.querySelectorAll('td');
                if (cells.length >= 4) {
                    items.push({
                        stt: cells[0]?.textContent?.trim() || '',
                        date: cells[1]?.textContent?.trim() || '',
                        amount: cells[2]?.textContent?.trim() || '',
                        refNo: cells[3]?.textContent?.trim() || '',
                        description: cells[4]?.textContent?.trim() || '',
                    });
                }
            });
            let balance = '';
            const allText = document.body.innerText;
            const balanceMatch = allText.match(/(?:Số dư|Dư nợ|Số dư khả dụng|Available Balance)[:\s]*([\d.,]+)/i);
            if (balanceMatch) {
                balance = balanceMatch[1].replace(/\./g, '').replace(/,/g, '');
            } else {
                const els = document.querySelectorAll('.balance, .account-balance, [class*="balance"], [class*="sodu"]');
                for (const el of els) {
                    const txt = el.textContent.trim();
                    if (/[\d.,]+/.test(txt)) {
                        balance = txt.replace(/[^\d]/g, '');
                        break;
                    }
                }
            }
            return { items, balance };
        });
        const tranList = items.map(item => {
            const amountStr = item.amount.replace(/[,\s]/g, '');
            const isCredit = !amountStr.startsWith('-');
            const amount = Math.abs(parseInt(amountStr) || 0);
            const signedAmount = isCredit ? `+${amount}` : `-${amount}`;
            return {
                refNo: item.refNo, tranId: item.refNo,
                postingDate: item.date, transactionDate: item.date,
                accountNo: CONFIG.stk,
                amount: signedAmount,
                creditAmount: isCredit ? String(amount) : '0',
                debitAmount: isCredit ? '0' : String(amount),
                currency: 'VND', description: item.description,
                availableBalance: balance, beneficiaryAccount: '',
            };
        });
        lastHistoryData = { status: 'success', message: 'Thành công', availableBalance: balance, TranList: tranList, timestamp: new Date().toISOString() };
        lastHistoryTime = Date.now();
        try { await page.goto(MBBANK_URL, { waitUntil: 'domcontentloaded', timeout: 10000 }); } catch(e) {}
        return lastHistoryData;
    } catch(e) {
        if (e.message.includes('Session') || e.message.includes('login')) { loggedIn = false; }
        throw e;
    }
}

// Auto-relogin removed - will only login when needed

const server = http.createServer(async (req, res) => {
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Content-Type', 'application/json; charset=utf-8');
    const url = new URL(req.url, `http://localhost:${PORT}`);
    const path = url.pathname;
    try {
        if (path === '/api/status') {
            return res.end(JSON.stringify({
                status: loggedIn ? 'logged_in' : 'not_logged_in',
                stk: CONFIG.stk,
                session_age: loggedIn ? Math.round((Date.now() - lastRefresh) / 1000) + 's' : null,
                history_age: lastHistoryData ? Math.round((Date.now() - lastHistoryTime) / 1000) + 's' : null,
            }));
        }
        if (path === '/api/login') {
            const result = await login();
            res.writeHead(200);
            return res.end(JSON.stringify(result));
        }
        if (path === '/api/history') {
            if (lastHistoryData && (Date.now() - lastHistoryTime) < 30000) {
                return res.end(JSON.stringify(lastHistoryData));
            }
            if (!loggedIn) {
                console.log('🔄 Session expired, auto-login...');
                await login();
            }
            const result = await getHistory();
            res.writeHead(200);
            return res.end(JSON.stringify(result));
        }
        res.writeHead(200);
        res.end(JSON.stringify({ name: 'MBBank API', endpoints: ['/api/status', '/api/login', '/api/history'] }));
    } catch(e) {
        res.writeHead(500);
        res.end(JSON.stringify({ status: 'error', message: e.message }));
    }
});

server.listen(PORT, '0.0.0.0', async () => {
    console.log(`MBBank API: http://0.0.0.0:${PORT}`);
    try { await login(); } catch(e) {}
});
