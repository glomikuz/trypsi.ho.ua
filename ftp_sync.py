#!/usr/bin/env python3
"""
FTP Sync Script (Download / Upload)
Використовує тільки стандартну бібліотеку Python 3.
Забезпечує перевірку розмірів файлів через LIST (без помилок 550 TYPE A SIZE) та Progress Bar.
"""

import sys
import os
import ftplib
import argparse
import time
from pathlib import Path

def load_env(env_path=".env"):
    """Зчитує конфігурацію з файлу .env"""
    env_vars = {}
    if not os.path.exists(env_path):
        print(f"❌ Помилка: Файл {env_path} не знайдено!")
        print("Скопіюйте .env.example в .env і вкажіть реквізити FTP:")
        print("  cp .env.example .env")
        sys.exit(1)
        
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env_vars[k.strip()] = v.strip().strip('"').strip("'")
    return env_vars

IGNORE_LIST = {".git", ".env", ".env.example", ".DS_Store", "__pycache__", ".gitignore", "*.tmp", "backup", "backups"}

def should_ignore(name):
    basename = os.path.basename(name)
    if basename in IGNORE_LIST or basename.startswith(".env") or basename.lower() == "backup":
        return True
    return False

def fmt_size(num):
    """Форматування байтів у людські одиниці (KB, MB, GB)"""
    if num is None:
        return "? B"
    for unit in ['B', 'KB', 'MB', 'GB']:
        if abs(num) < 1024.0:
            return f"{num:3.1f} {unit}"
        num /= 1024.0
    return f"{num:.1f} TB"

def print_progress(transferred, total, filename, prefix="⬇"):
    """Малює прогрес-бар передачі файлу"""
    if total and total > 0:
        percent = min(100.0, (transferred / total) * 100)
        bar_len = 20
        filled = int(bar_len * transferred // total)
        bar = '=' * filled + '-' * (bar_len - filled)
        tot_str = fmt_size(total)
    else:
        percent = 0.0
        bar = '-' * 20
        tot_str = "? B"

    t_str = fmt_size(transferred)
    fn_display = filename if len(filename) <= 25 else filename[:22] + "..."
    sys.stdout.write(f"\r  {prefix} [{percent:5.1f}%] [{bar}] {t_str} / {tot_str} | {fn_display:<25}")
    sys.stdout.flush()

def connect_ftp(cfg):
    host = cfg.get("FTP_HOST")
    user = cfg.get("FTP_USER")
    passwd = cfg.get("FTP_PASS")
    port = int(cfg.get("FTP_PORT", 21))
    pasv = cfg.get("FTP_PASV", "true").lower() == "true"
    use_ssl = cfg.get("FTP_SSL", "false").lower() == "true"

    if not host or not user or not passwd:
        print("❌ Помилка: В .env файлі не заповнено FTP_HOST, FTP_USER або FTP_PASS!")
        sys.exit(1)

    print(f"🔌 Підключення до FTP {host}:{port}...")
    if use_ssl:
        ftp = ftplib.FTP_TLS()
    else:
        ftp = ftplib.FTP()

    ftp.connect(host, port, timeout=60)
    ftp.login(user, passwd)
    ftp.set_pasv(pasv)
    if use_ssl:
        ftp.prot_p()

    print("✔ З'єднання успішно встановлено!\n")
    return ftp

def get_remote_directory_items(ftp):
    """
    Повертає словник {назва: (is_dir, size_in_bytes)} з використанням LIST.
    Це усуває помилки '550 TYPE A SIZE' та прискорює сканування у 10 разів.
    """
    lines = []
    try:
        ftp.dir(lines.append)
    except Exception as e:
        return {}

    items = {}
    for line in lines:
        parts = line.split(maxsplit=8)
        if len(parts) >= 9:
            perms, _, _, _, size_str, _, _, _, name = parts
            if name in ('.', '..'):
                continue
            is_dir = perms.startswith('d')
            try:
                size = int(size_str) if not is_dir else None
            except ValueError:
                size = None
            items[name] = (is_dir, size)
    return items

def ensure_remote_dir(ftp, remote_dir):
    parts = [p for p in remote_dir.split('/') if p]
    current = ""
    for part in parts:
        current += "/" + part
        try:
            ftp.cwd(current)
        except ftplib.error_perm:
            try:
                ftp.mkd(current)
                print(f"  [+] Створено віддалену папку: {current}")
            except Exception:
                pass

def upload_sync(ftp, local_base, remote_base, cfg):
    print(f"🚀 Вивантаження змін (Upload) з '{local_base}' на FTP '{remote_base}'...")
    local_base = os.path.abspath(local_base)

    transferred_count = 0
    skipped_count = 0

    for root, dirs, files in os.walk(local_base):
        dirs[:] = [d for d in dirs if not should_ignore(d)]
        
        rel_path = os.path.relpath(root, local_base)
        if rel_path == ".":
            current_remote = remote_base
        else:
            current_remote = os.path.join(remote_base, rel_path).replace("\\", "/")

        ensure_remote_dir(ftp, current_remote)
        ftp.cwd(current_remote)
        
        remote_items = get_remote_directory_items(ftp)

        for fname in files:
            if should_ignore(fname):
                continue

            local_file = os.path.join(root, fname)
            l_size = os.path.getsize(local_file)
            
            r_info = remote_items.get(fname)
            r_size = r_info[1] if r_info else None

            # Якщо розмір збігається — пропускаємо (не перекачуємо знову)
            if r_size == l_size:
                skipped_count += 1
                sys.stdout.write(f"\r  ⏩ [Пропущено] {fname:<35} ({fmt_size(l_size)})\n")
                sys.stdout.flush()
                continue

            transferred_bytes = 0
            def callback(chunk):
                nonlocal transferred_bytes
                transferred_bytes += len(chunk)
                print_progress(transferred_bytes, l_size, fname, prefix="⬆ Upload")

            try:
                with open(local_file, "rb") as f:
                    ftp.storbinary(f"STOR {fname}", f, callback=callback)
            except (socket_error if 'socket_error' in globals() else Exception) as err:
                print(f"\n⚠️ З'єднання перервано ({err}). Перепідключення...")
                ftp = connect_ftp(cfg)
                ftp.cwd(current_remote)
                with open(local_file, "rb") as f:
                    ftp.storbinary(f"STOR {fname}", f, callback=callback)

            sys.stdout.write("\n")
            transferred_count += 1

    print(f"\n📊 Підсумок: Завантажено файлів: {transferred_count}, Пропущено (без змін): {skipped_count}")

def download_sync(ftp, remote_base, local_base, cfg):
    print(f"📥 Завантаження змін (Download) з FTP '{remote_base}' в '{local_base}'...")
    os.makedirs(local_base, exist_ok=True)

    transferred_count = 0
    skipped_count = 0

    def sync_folder(r_path, l_path):
        nonlocal transferred_count, skipped_count, ftp
        try:
            ftp.cwd(r_path)
        except Exception as e:
            print(f"\n❌ Не вдалося відкрити віддалену папку '{r_path}': {e}")
            return

        remote_items = get_remote_directory_items(ftp)

        for item, (is_dir, r_size) in remote_items.items():
            if should_ignore(item):
                continue

            local_item_path = os.path.join(l_path, item)

            if is_dir:
                os.makedirs(local_item_path, exist_ok=True)
                r_subdir = r_path.rstrip("/") + "/" + item
                sync_folder(r_subdir, local_item_path)
                try:
                    ftp.cwd(r_path)
                except Exception:
                    ftp = connect_ftp(cfg)
                    ftp.cwd(r_path)
            else:
                l_size = os.path.getsize(local_item_path) if os.path.exists(local_item_path) else None

                # Якщо розмір збігається — пропускаємо
                if l_size is not None and r_size is not None and l_size == r_size:
                    skipped_count += 1
                    sys.stdout.write(f"\r  ⏩ [Пропущено] {item:<35} ({fmt_size(r_size)})\n")
                    sys.stdout.flush()
                    continue

                transferred_bytes = 0
                try:
                    with open(local_item_path, "wb") as f:
                        def callback(data):
                            nonlocal transferred_bytes
                            f.write(data)
                            transferred_bytes += len(data)
                            print_progress(transferred_bytes, r_size, item, prefix="⬇ Download")

                        ftp.retrbinary(f"RETR {item}", callback)
                except Exception as err:
                    print(f"\n⚠️ З'єднання перервано ({err}). Перепідключення...")
                    ftp = connect_ftp(cfg)
                    ftp.cwd(r_path)
                    with open(local_item_path, "wb") as f:
                        def callback(data):
                            nonlocal transferred_bytes
                            f.write(data)
                            transferred_bytes += len(data)
                            print_progress(transferred_bytes, r_size, item, prefix="⬇ Download")

                        ftp.retrbinary(f"RETR {item}", callback)

                sys.stdout.write("\n")
                transferred_count += 1

    sync_folder(remote_base, local_base)
    print(f"\n📊 Підсумок: Завантажено файлів: {transferred_count}, Пропущено (без змін): {skipped_count}")

def main():
    parser = argparse.ArgumentParser(description="Скрипт синхронізації FTP (Download / Upload)")
    parser.add_argument("action", choices=["download", "upload", "down", "up", "pull", "push"],
                        help="Дія: download (скачати) або upload (вивантажити)")
    parser.add_argument("--env", default=".env", help="Шлях до .env файлу (за замовчуванням: .env)")

    args = parser.parse_args()
    cfg = load_env(args.env)

    local_dir = cfg.get("LOCAL_DIR", "./htdocs")
    remote_dir = cfg.get("REMOTE_DIR", "/htdocs")

    ftp = connect_ftp(cfg)

    try:
        if args.action in ("download", "down", "pull"):
            download_sync(ftp, remote_dir, local_dir, cfg)
        elif args.action in ("upload", "up", "push"):
            upload_sync(ftp, local_dir, remote_dir, cfg)
        ftp.quit()
        print("\n✨ Готово! Операцію завершено успішно.")
    except KeyboardInterrupt:
        print("\n⚠️ Перервано користувачем.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Виникла помилка: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
