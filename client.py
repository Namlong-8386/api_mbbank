import requests

BASE_URL = 'http://127.0.0.1:5000'


def main():
    print('Nhập thông tin đăng nhập MBBank')
    phone = input('MB_PHONE: ').strip()
    password = input('MB_PASSWORD: ').strip()
    stk = input('MB_STK: ').strip()

    print('\n🔄 Đang gọi API lấy lịch sử...')
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
    except requests.exceptions.ConnectionError:
        print('❌ Không kết nối được server.')
        print('Hãy chạy workflow "Start application" hoặc chạy `python run.py` trước.')
    except Exception as e:
        print('❌ Lỗi:', e)


if __name__ == '__main__':
    main()
