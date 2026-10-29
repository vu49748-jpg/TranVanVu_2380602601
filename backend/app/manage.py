import argparse
import getpass
from sqlalchemy import select
from .db import Base, engine, SessionLocal, User
from .schemas import Register
from .security import passwords

def main():
    parser = argparse.ArgumentParser(description='Quản trị tài khoản project TranVanVu_2380602601')
    parser.add_argument('command', choices=['create-admin'])
    parser.add_argument('--email', required=True)
    parser.add_argument('--username', default='tranvanvu')
    args = parser.parse_args()
    password = getpass.getpass('Mật khẩu admin (ít nhất 8 ký tự): ')
    if password != getpass.getpass('Nhập lại mật khẩu: '): raise SystemExit('Mật khẩu không khớp.')
    data = Register(email=args.email, username=args.username, password=password, full_name='Trần Văn Vũ')
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.username == data.username)): raise SystemExit('Tên đăng nhập đã tồn tại.')
        db.add(User(**data.model_dump(exclude={'password'}), role='admin', password_hash=passwords.hash(data.password)))
        db.commit()
    print('Đã tạo admin. Lần đăng nhập đầu tiên vẫn cần Email OTP để xác thực email.')

if __name__ == '__main__': main()
