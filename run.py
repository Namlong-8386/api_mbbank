import os

os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
os.environ["CUDA_VISIBLE_DEVICES"] = ""

import asyncio
import base64
import datetime
import time
from threading import Lock, Thread

import numpy as np
import tensorflow as tf
from flask import Flask, jsonify, request
from flask_cors import CORS, cross_origin
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
import tf_keras as keras
from tf_keras import layers
from tf_keras.models import model_from_json

app = Flask(__name__)
CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'

# ----------------------------
# Captcha model config
# ----------------------------
characters_mb = ['K', 'M', 'C', 'e', 'g', 'k', 'u', 'z', 't', '3', 'U', 'a', '5', 'A', 'y', 'H', 'q', 'Z', 'V', '7', 'Q', '2', '4', 'Y', '-', 'h', '8', 'v', '6', 'd', 'b', 'n', 'p', 'P', 'E', 'c', 'm', 'D', 'B', '9', 'N', 'G']
img_width = 320
img_height = 80
max_length = 15

char_to_num_mb = layers.StringLookup(vocabulary=list(characters_mb), mask_token=None)
num_to_char_mb = layers.StringLookup(
    vocabulary=char_to_num_mb.get_vocabulary(), mask_token=None, invert=True
)

# Load captcha model once at startup
print("Loading captcha model...")
with open('model_mb.json', 'r') as json_file_mb:
    loaded_model_json = json_file_mb.read()
loaded_model_mb = model_from_json(loaded_model_json)
loaded_model_mb.load_weights("model_mb.h5")
model_lock = Lock()
print("Captcha model loaded.")


def standardize_base64(s: str) -> str:
    """Convert URL-safe base64 to standard base64 and fix padding."""
    s = s.replace('-', '+').replace('_', '/')
    pad = len(s) % 4
    if pad:
        s += '=' * (4 - pad)
    return s


def encode_base64x(img_b64: str):
    # Dùng base64 của Python để tránh lỗi "Invalid character found in base64" của tf.io.decode_base64
    import base64
    img_bytes = base64.b64decode(standardize_base64(img_b64))
    img = tf.io.decode_png(tf.constant(img_bytes), channels=1)
    img = tf.image.convert_image_dtype(img, tf.float32)
    img = tf.image.resize(img, [img_height, img_width])
    img = tf.transpose(img, perm=[1, 0, 2])
    return {"image": img}


def decode_batch_predictions(pred):
    input_len = np.ones(pred.shape[0]) * pred.shape[1]
    results = keras.backend.ctc_decode(pred, input_length=input_len, greedy=True)[0][0][:, :max_length]
    results = tf.strings.reduce_join(num_to_char_mb(results)).numpy().decode("utf-8")
    return [results]


def solve_captcha_local(img_b64: str) -> str:
    import re
    clean = img_b64.strip() if img_b64 else ''
    invalid = set(re.findall(r'[^A-Za-z0-9+/=]', clean))
    if invalid:
        print(f'⚠️ Invalid base64 chars: {invalid}')
    print(f'🔤 Captcha base64 length: {len(clean)}, last 10 chars: {clean[-10:]}')
    with model_lock:
        image_encode = encode_base64x(clean)["image"]
        listImage = np.array([image_encode])
        preds = loaded_model_mb.predict(listImage, verbose=0)
        pred_texts = decode_batch_predictions(preds)
        captcha = pred_texts[0].replace('[UNK]', '').replace('-', '')
    return captcha


# ----------------------------
# MBBank browser automation
# ----------------------------
MBBANK_URL = 'https://online.mbbank.com.vn'
CONFIG = {
    'phone': os.getenv('MB_PHONE', ''),
    'password': os.getenv('MB_PASSWORD', ''),
    'stk': os.getenv('MB_STK', ''),
}


class MBBankSession:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.page = None
        self.logged_in = False
        self.last_refresh = 0
        self.last_history_data = None
        self.last_history_time = 0
        self.login_in_progress = False
        self.lock = Lock()

    async def init_browser(self):
        if self.browser and self.page:
            return
        if self.browser:
            try:
                await self.browser.close()
            except Exception:
                pass
        self.playwright = await async_playwright().start()
        # Dùng Chrome đầy đủ thay vì headless shell để tránh bị Akamai chặn
        chrome_path = await self._find_chrome_executable()
        launch_args = [
            '--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage',
            '--disable-gpu', '--disable-images', '--disable-extensions',
            '--disable-background-networking', '--disable-sync'
        ]
        launch_kwargs = {'headless': True, 'args': launch_args}
        if chrome_path:
            launch_kwargs['executable_path'] = chrome_path
        self.browser = await self.playwright.chromium.launch(**launch_kwargs)
        context = await self.browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            extra_http_headers={'Accept-Language': 'vi-VN,vi;q=0.9'}
        )
        await context.route('**/*', self._block_resources)
        self.page = await context.new_page()
        stealth = Stealth()
        await stealth.apply_stealth_async(self.page)
        self.logged_in = False

    async def _find_chrome_executable(self):
        from pathlib import Path
        home = Path.home()
        candidates = [
            Path('.cache/ms-playwright/chromium-1228/chrome-linux64/chrome').resolve(),
            home / '.cache/ms-playwright/chromium-1228/chrome-linux64/chrome',
        ]
        for candidate in candidates:
            if candidate.exists():
                return str(candidate)
        return None

    async def _block_resources(self, route, request):
        if request.resource_type in ['image', 'stylesheet', 'font', 'media']:
            await route.abort()
        else:
            await route.continue_()

    async def get_captcha_base64(self):
        return await self.page.evaluate('''() => {
            const imgs = document.querySelectorAll('img');
            for (const img of imgs) {
                if (img.src && img.src.startsWith('data:image/png;base64,')) {
                    return img.src.replace('data:image/png;base64,', '');
                }
            }
            return null;
        }''')

    async def login(self):
        with self.lock:
            if self.login_in_progress:
                return {'success': False, 'message': 'Đang login...'}
            self.login_in_progress = True

        try:
            if not CONFIG['phone'] or not CONFIG['password'] or not CONFIG['stk']:
                return {
                    'success': False,
                    'message': 'Thiếu thông tin đăng nhập (MB_PHONE, MB_PASSWORD, MB_STK)'
                }

            await self.init_browser()
            print('📱 Mở MBBank...')
            await self.page.goto(MBBANK_URL, wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(0.5)
            await self.page.type('#user-id', CONFIG['phone'], delay=5)
            await self.page.type('#new-password', CONFIG['password'], delay=5)

            captcha_base64 = await self.get_captcha_base64()
            if not captcha_base64:
                raise Exception('Không tìm thấy captcha')

            print('🤖 Giải captcha...')
            captcha_text = solve_captcha_local(captcha_base64)
            if not captcha_text:
                raise Exception('Giải captcha thất bại')
            print('📝 Captcha:', captcha_text)

            captcha_input = self.page.locator('input[placeholder*="MÃ KIỂM TRA"]').first
            if await captcha_input.count() > 0:
                await captcha_input.click(click_count=3)
                await captcha_input.type(captcha_text, delay=5)

            await self.page.click('button.btnma')
            await asyncio.sleep(1)

            text = await self.page.inner_text('body')
            if 'captcha không chính xác' in text:
                raise Exception('Sai captcha')
            if 'sai' in text or 'incorrect' in text or 'GW' in text:
                raise Exception('Sai thông tin')

            self.logged_in = True
            self.last_refresh = time.time()
            print('✅ Login thành công!')
            return {'success': True}
        except Exception as e:
            print('❌ Login failed:', str(e))
            return {'success': False, 'message': str(e)}
        finally:
            self.login_in_progress = False

    async def get_history(self):
        if not self.logged_in or not self.page:
            raise Exception('Chưa login')

        try:
            await self.page.goto(
                f'{MBBANK_URL}/information-account/source-account',
                wait_until='domcontentloaded', timeout=30000
            )
            await asyncio.sleep(1.5)

            url = self.page.url
            if 'login' in url:
                self.logged_in = False
                raise Exception('Session hết hạn')

            await self.page.evaluate('''() => {
                const btns = document.querySelectorAll('button, a');
                for (const btn of btns) {
                    if (btn.textContent && btn.textContent.includes('Truy vấn')) {
                        btn.click();
                        return;
                    }
                }
            }''')
            await asyncio.sleep(2)

            data = await self.page.evaluate('''() => {
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
                const balanceMatch = allText.match(/TỔNG SỐ DƯ[\s\S]{0,500}?(\d{1,3}(?:,\d{3})+)\s*VND/i) ||
                                      allText.match(/(?:Số dư|Dư nợ|Số dư khả dụng|Available Balance)[:\s]*([\d.,]+)/i);
                if (balanceMatch) {
                    balance = balanceMatch[1].replace(/\./g, '').replace(/,/g, '');
                } else {
                    const els = document.querySelectorAll('.balance, .account-balance, [class*="balance"], [class*="sodu"]');
                    for (const el of els) {
                        const txt = el.textContent.trim();
                        if (/^[\d.,]+$/.test(txt)) {
                            balance = txt.replace(/[^\d]/g, '');
                            break;
                        }
                    }
                }
                return { items, balance };
            }''')

            items = data['items']
            balance = data['balance']
            tran_list = []
            for item in items:
                amount_str = item['amount'].replace(',', '').replace(' ', '')
                is_credit = not amount_str.startswith('-')
                amount = abs(int(amount_str) if amount_str else 0)
                signed_amount = f'+{amount}' if is_credit else f'-{amount}'
                tran_list.append({
                    'refNo': item['refNo'],
                    'tranId': item['refNo'],
                    'postingDate': item['date'],
                    'transactionDate': item['date'],
                    'accountNo': CONFIG['stk'],
                    'amount': signed_amount,
                    'creditAmount': str(amount) if is_credit else '0',
                    'debitAmount': '0' if is_credit else str(amount),
                    'currency': 'VND',
                    'description': item['description'],
                    'availableBalance': balance,
                    'beneficiaryAccount': '',
                })

            self.last_history_data = {
                'status': 'success',
                'message': 'Thành công',
                'availableBalance': balance,
                'TranList': tran_list,
                'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat()
            }
            self.last_history_time = time.time()

            try:
                await self.page.goto(MBBANK_URL, wait_until='domcontentloaded', timeout=10000)
            except Exception:
                pass

            return self.last_history_data
        except Exception as e:
            if 'Session' in str(e) or 'login' in str(e):
                self.logged_in = False
            raise


class BrowserWorker:
    """Chạy tất cả thao tác Playwright trong một thread/event loop duy nhất
    để tránh lỗi khi dùng asyncio.run() nhiều lần với cùng một browser session."""
    def __init__(self, session):
        self.session = session
        self.loop = asyncio.new_event_loop()
        self.thread = Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def _run_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def run(self, coro, timeout=300):
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        return future.result(timeout=timeout)


mb_session = MBBankSession()
worker = BrowserWorker(mb_session)


# ----------------------------
# Flask routes
# ----------------------------
@app.route('/api/captcha/mbbank', methods=['POST'])
@cross_origin(origin='*')
def captcha_endpoint():
    content = request.json or {}
    imgstring = content.get('base64', '')
    if not imgstring:
        return jsonify(status='error', message='Thiếu base64'), 400
    try:
        captcha = solve_captcha_local(imgstring)
        return jsonify(status='success', captcha=captcha)
    except Exception as e:
        return jsonify(status='error', message=str(e)), 500


@app.route('/api/status')
def status():
    return jsonify(
        status='logged_in' if mb_session.logged_in else 'not_logged_in',
        stk=CONFIG['stk'],
        session_age=f'{int(time.time() - mb_session.last_refresh)}s' if mb_session.logged_in else None,
        history_age=f'{int(time.time() - mb_session.last_history_time)}s' if mb_session.last_history_data else None,
    )


@app.route('/api/login', methods=['POST', 'GET'])
def login_endpoint():
    result = worker.run(mb_session.login())
    return jsonify(result)


@app.route('/api/history', methods=['POST', 'GET'])
def history_endpoint():
    if mb_session.last_history_data and (time.time() - mb_session.last_history_time) < 30:
        return jsonify(mb_session.last_history_data)
    if not mb_session.logged_in:
        print('🔄 Session expired, auto-login...')
        worker.run(mb_session.login())
    try:
        result = worker.run(mb_session.get_history())
        return jsonify(result)
    except Exception as e:
        return jsonify(status='error', message=str(e)), 500


@app.route('/')
def index():
    return jsonify({
        'name': 'MBBank API',
        'endpoints': ['/api/status', '/api/login', '/api/history', '/api/captcha/mbbank']
    })


@app.errorhandler(500)
def handle_500(e):
    return jsonify(status='error', message=str(e)), 500


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, threaded=True)
