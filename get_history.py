"""Script tự động: nhập credentials, khởi động server, lấy lịch sử."""
import os
import subprocess
import sys
import time

import requests

BASE_URL = 'http://127.0.0.1:5000'


def is_server_running():
    try:
        requests.get(f'{BASE_URL}/', timeout=2)
        return True
    except Exception:
        return False


def main():
    print('Nhập thông tin đăng nhập MBBank')
    phone = input('MB_PHONE: ').strip()
    password = input('MB_PASSWORD: ').strip()
    stk = input('MB_STK: ').strip()

    # Nếu server chưa chạy thì khởi động trong subprocess.
    server = None
    if not is_server_running():
        print('\n🚀 Server chưa chạy, đang khởi động...')
        env = os.environ.copy()
        env['MB_PHONE'] = phone
        env['MB_PASSWORD'] = password
        env['MB_STK'] = stk
        server = subprocess.Popen([sys.executable, 'run.py'], env=env)
        print('⏳ Chờ server khởi động...')
        for _ in range(30):
            if is_server_running():
                break
            time.sleep(1)
        else:
            print('❌ Server không khởi động được.')
            if server:
                server.terminate()
            return
    else:
        print('\n✅ Server đã chạy.')

    print('🔄 Đang lấy lịch sử...')
    print('(Lần đầu cần mở trình duyệt + giải captcha + login, có thể mất 30-60 giây)')

    try:
        resp = requests.post(
            f'{BASE_URL}/api/history',
            json={'phone': phone, 'password': password, 'stk': stk},
            timeout=300
        )
        data = resp.json()

        if resp.status_code != 200 or data.get('status') == 'error':
            print('❌ Lỗi:', data.get('message', resp.text))
            return

        print('\n✅ Số dư khả dụng:', data.get('availableBalance'))
        print('📜 Lịch sử giao dịch:')
        for i, tx in enumerate(data.get('TranList', []), start=1):
            print(f"{i}. {tx.get('postingDate')} | {tx.get('amount')} VND | {tx.get('description')} | Ref: {tx.get('refNo')}")
    except Exception as e:
        print('❌ Lỗi:', e)
    finally:
        if server:
            print('\n🛑 Dừng server...')
            server.terminate()


if __name__ == '__main__':
    main()
