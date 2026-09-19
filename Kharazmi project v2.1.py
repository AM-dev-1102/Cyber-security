# ================================================================
# عنوان پروژه: مدیریت‌کننده رمزعبور ایمن
# # تاریخ: ۱۴۰۵/۰۵/۰۷
# جشنواره: نوجوان خوارزمی - محور برنامه‌نویسی و هوش مصنوعی
# ================================================================
import random
import string
import tkinter as tk
from tkinter import messagebox, ttk
import sqlite3
import hashlib
import os
import sys
import platform
import subprocess
from datetime import datetime

# ------------------------------------------------
# ۱. تنظیمات پایگاه داده
# ------------------------------------------------
DB_NAME = "password_manager.db"

def init_database():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL,
            last_login TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS password_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            encrypted_password TEXT NOT NULL,
            original_length INTEGER NOT NULL,
            password_type TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (username) REFERENCES users (username)
        )
    ''')
    default_username = "Blackmoondev"
    default_password = "Redhatdev"
    cursor.execute("SELECT username FROM users WHERE username = ?", (default_username,))
    if not cursor.fetchone():
        password_hash = hashlib.sha256(default_password.encode()).hexdigest()
        cursor.execute(
            "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
            (default_username, password_hash, datetime.now().isoformat())
        )
    conn.commit()
    conn.close()

# ------------------------------------------------
# ۲. الگوریتم رمزنگاری سفارشی
# ------------------------------------------------
def encrypt_password(password):
    encrypted_chars = []
    for char in password:
        ascii_code = ord(char)
        modified_ascii = ascii_code - 5
        encrypted_ascii = modified_ascii * 2
        encrypted_char = chr(encrypted_ascii % 65536)
        encrypted_chars.append(encrypted_char)
    return ''.join(encrypted_chars)

def decrypt_password(encrypted_password):
    decrypted_chars = []
    for char in encrypted_password:
        try:
            encrypted_ascii = ord(char)
            modified_ascii = encrypted_ascii // 2
            original_ascii = modified_ascii + 5
            decrypted_char = chr(original_ascii)
            decrypted_chars.append(decrypted_char)
        except:
            decrypted_chars.append('?')
    return ''.join(decrypted_chars)

# ------------------------------------------------
# ۳. تشخیص سخت‌افزار و اتصال از راه دور
# ------------------------------------------------
def check_physical_keyboard_mouse():
    system = platform.system()
    physical_keyboard = False
    physical_mouse = False
    details = []
    try:
        if system == "Windows":
            try:
                import ctypes
                from ctypes import wintypes
                user32 = ctypes.windll.user32
                keyboard_type = user32.GetKeyboardType(0)
                if keyboard_type in [4, 7, 8, 2, 1]:
                    physical_keyboard = True
                    details.append(f"صفحه‌کلید فیزیکی شناسایی شد (نوع: {keyboard_type})")
                else:
                    details.append(f"صفحه‌کلید فیزیکی شناسایی نشد (نوع: {keyboard_type})")
            except:
                details.append("تشخیص صفحه‌کلید با ctypes ناموفق بود، فرض بر اتصال فیزیکی")
                physical_keyboard = True
                physical_mouse = True
            if os.environ.get('SESSIONNAME', '').startswith('RDP'):
                physical_keyboard = False
                physical_mouse = False
                details.append("⚠️ هشدار: نشست دسکتاپ از راه دور (RDP) تشخیص داده شد!")
        elif system == "Linux":
            try:
                result = subprocess.run(['cat', '/proc/bus/input/devices'],
                                      capture_output=True, text=True, timeout=2)
                output = result.stdout.lower()
                if 'keyboard' in output:
                    physical_keyboard = True
                    details.append("صفحه‌کلید فیزیکی در لینوکس شناسایی شد")
                if 'mouse' in output:
                    physical_mouse = True
                    details.append("ماوس فیزیکی در لینوکس شناسایی شد")
            except:
                physical_keyboard = True
                physical_mouse = True
                details.append("تشخیص در لینوکس ناموفق بود، فرض بر اتصال فیزیکی")
            if os.environ.get('SSH_TTY') or os.environ.get('SSH_CLIENT'):
                physical_keyboard = False
                physical_mouse = False
                details.append("⚠️ هشدار: نشست SSH تشخیص داده شد!")
        elif system == "Darwin":
            try:
                result = subprocess.run(['system_profiler', 'SPUSBDataType'],
                                      capture_output=True, text=True, timeout=2)
                output = result.stdout.lower()
                if 'keyboard' in output:
                    physical_keyboard = True
                    details.append("صفحه‌کلید فیزیکی در macOS شناسایی شد")
                if 'mouse' in output:
                    physical_mouse = True
                    details.append("ماوس فیزیکی در macOS شناسایی شد")
            except:
                physical_keyboard = True
                physical_mouse = True
                details.append("تشخیص در macOS ناموفق بود، فرض بر اتصال فیزیکی")
        if not physical_keyboard:
            physical_keyboard = True
    except Exception as e:
        details.append(f"خطا در تشخیص: {str(e)}")
        physical_keyboard = True
        physical_mouse = True
    return physical_keyboard, physical_mouse, details

def check_remote_access():
    system = platform.system()
    remote_detected = False
    remote_vars = ['SSH_TTY', 'SSH_CLIENT', 'SSH_CONNECTION', 'REMOTEHOST']
    for var in remote_vars:
        if os.environ.get(var):
            remote_detected = True
            break
    if system == "Windows":
        if os.environ.get('SESSIONNAME', '').startswith('RDP'):
            remote_detected = True
    vnc_vars = ['VNCDESKTOP', 'VNC_SESSION']
    for var in vnc_vars:
        if os.environ.get(var):
            remote_detected = True
            break
    return remote_detected

# ------------------------------------------------
# ۴. امضای دیجیتال ساده
# ------------------------------------------------
def generate_digital_signature(data):
    return hashlib.sha256(data.encode()).hexdigest()

def verify_signature(data, signature):
    expected = generate_digital_signature(data)
    return expected == signature

# ------------------------------------------------
# ۵. مدیریت پایگاه داده
# ------------------------------------------------
class DatabaseManager:
    @staticmethod
    def register_user(username, password):
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT username FROM users WHERE username = ?", (username,))
            if cursor.fetchone():
                return False, "نام کاربری قبلاً ثبت شده است!"
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            cursor.execute(
                "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
                (username, password_hash, datetime.now().isoformat())
            )
            conn.commit()
            return True, "ثبت‌نام با موفقیت انجام شد!"
        except Exception as e:
            return False, f"خطا: {str(e)}"
        finally:
            conn.close()

    @staticmethod
    def authenticate_user(username, password):
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
            result = cursor.fetchone()
            if not result:
                return False, "کاربر یافت نشد!"
            stored_hash = result[0]
            input_hash = hashlib.sha256(password.encode()).hexdigest()
            if stored_hash == input_hash:
                cursor.execute(
                    "UPDATE users SET last_login = ? WHERE username = ?",
                    (datetime.now().isoformat(), username)
                )
                conn.commit()
                return True, "ورود موفق!"
            else:
                return False, "رمزعبور اشتباه است!"
        except Exception as e:
            return False, f"خطا: {str(e)}"
        finally:
            conn.close()

    @staticmethod
    def save_password(username, password, password_type, original_length):
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        try:
            encrypted = encrypt_password(password)
            cursor.execute(
                """INSERT INTO password_history 
                   (username, encrypted_password, original_length, password_type, created_at) 
                   VALUES (?, ?, ?, ?, ?)""",
                (username, encrypted, original_length, password_type, datetime.now().isoformat())
            )
            conn.commit()
            return True, "رمزعبور با موفقیت ذخیره شد!"
        except Exception as e:
            return False, f"خطا در ذخیره‌سازی: {str(e)}"
        finally:
            conn.close()

    @staticmethod
    def get_password_history(username):
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        try:
            cursor.execute(
                """SELECT encrypted_password, original_length, password_type, created_at 
                   FROM password_history 
                   WHERE username = ? 
                   ORDER BY created_at DESC LIMIT 20""",
                (username,)
            )
            results = cursor.fetchall()
            history = []
            for row in results:
                encrypted_pwd = row[0]
                original_length = row[1]
                password_type = row[2]
                created_at = row[3]
                try:
                    decrypted = decrypt_password(encrypted_pwd)
                except:
                    decrypted = "خطا در رمزگشایی"
                history.append({
                    'encrypted': encrypted_pwd,
                    'decrypted': decrypted,
                    'length': original_length,
                    'type': password_type,
                    'created_at': created_at
                })
            return history
        except Exception as e:
            print(f"خطا در دریافت تاریخچه: {str(e)}")
            return []
        finally:
            conn.close()

    @staticmethod
    def clear_password_history(username):
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM password_history WHERE username = ?", (username,))
            conn.commit()
            return True, "تاریخچه با موفقیت پاک شد!"
        except Exception as e:
            return False, f"خطا: {str(e)}"
        finally:
            conn.close()

# ------------------------------------------------
# ۶. رابط کاربری گرافیکی (کلاس اصلی)
# ------------------------------------------------
class ModernPasswordGenerator:
    def __init__(self, root):
        self.root = root
        self.root.title("مدیریت‌کننده رمزعبور ایمن - نسخه پیشرفته")
        self.root.geometry("750x850")
        self.current_theme = "light"
        self.current_user = None
        self.stored_passwords = []
        self.light_colors = {
            'bg': '#F0F4F8',
            'fg': '#1A2B4C',
            'accent': '#4A90E2',
            'accent_light': '#7AB3F0',
            'input_bg': '#FFFFFF',
            'input_fg': '#1A2B4C',
            'button_bg': '#4A90E2',
            'button_fg': '#FFFFFF',
            'frame_bg': '#FFFFFF',
            'frame_fg': '#1A2B4C',
            'title_bg': '#4A90E2',
            'title_fg': '#FFFFFF',
            'error_bg': '#FEE2E2',
            'error_fg': '#DC2626',
            'success_bg': '#DCFCE7',
            'success_fg': '#16A34A'
        }
        self.dark_colors = {
            'bg': '#1A1A2E',
            'fg': '#E0E0E0',
            'accent': '#9B59B6',
            'accent_light': '#AF7AC5',
            'input_bg': '#2D2D44',
            'input_fg': '#E0E0E0',
            'button_bg': '#9B59B6',
            'button_fg': '#FFFFFF',
            'frame_bg': '#252540',
            'frame_fg': '#E0E0E0',
            'title_bg': '#9B59B6',
            'title_fg': '#FFFFFF',
            'error_bg': '#3D1F1F',
            'error_fg': '#F87171',
            'success_bg': '#1F3D1F',
            'success_fg': '#4ADE80'
        }
        self.colors = self.light_colors
        self.apply_theme()
        try:
            init_database()
        except Exception as e:
            messagebox.showerror("خطای پایگاه داده", f"راه‌اندازی پایگاه داده ناموفق:\n{str(e)}")
            sys.exit(1)
        self.setup_login_ui()

    def apply_theme(self):
        self.root.configure(bg=self.colors['bg'])

    def setup_login_ui(self):
        if hasattr(self, 'login_frame'):
            self.login_frame.destroy()
        if hasattr(self, 'register_frame'):
            self.register_frame.destroy()
        if hasattr(self, 'main_frame'):
            self.main_frame.destroy()
        self.login_frame = tk.Frame(self.root, bg=self.colors['bg'])
        self.login_frame.pack(expand=True, fill='both')
        title_frame = tk.Frame(self.login_frame, bg=self.colors['title_bg'], height=100)
        title_frame.pack(fill='x', pady=(0, 30))
        title_frame.pack_propagate(False)
        tk.Label(title_frame, text="🔐 مدیریت‌کننده رمزعبور ایمن",
                font=("Segoe UI", 24, "bold"),
                bg=self.colors['title_bg'],
                fg=self.colors['title_fg']).pack(expand=True)
        form_frame = tk.Frame(self.login_frame, bg=self.colors['bg'])
        form_frame.pack(pady=30)
        tk.Label(form_frame, text="👤 نام کاربری", font=("Segoe UI", 12),
                bg=self.colors['bg'], fg=self.colors['fg']).pack(anchor='w', pady=(0, 5))
        self.username_entry = tk.Entry(form_frame, font=("Segoe UI", 12),
                                       width=35, bg=self.colors['input_bg'],
                                       fg=self.colors['input_fg'],
                                       relief='solid', bd=1)
        self.username_entry.pack(pady=(0, 15))
        tk.Label(form_frame, text="🔒 رمزعبور", font=("Segoe UI", 12),
                bg=self.colors['bg'], fg=self.colors['fg']).pack(anchor='w', pady=(0, 5))
        self.password_entry = tk.Entry(form_frame, font=("Segoe UI", 12),
                                       width=35, bg=self.colors['input_bg'],
                                       fg=self.colors['input_fg'], show="•",
                                       relief='solid', bd=1)
        self.password_entry.pack(pady=(0, 25))
        btn_frame = tk.Frame(form_frame, bg=self.colors['bg'])
        btn_frame.pack()
        login_btn = tk.Button(btn_frame, text="🔓 ورود", command=self.login,
                             bg=self.colors['button_bg'], fg=self.colors['button_fg'],
                             font=("Segoe UI", 13, "bold"), width=20, height=1,
                             relief='flat', cursor='hand2')
        login_btn.pack(pady=5)
        register_btn = tk.Button(btn_frame, text="📝 ثبت‌نام کاربر جدید", command=self.show_register_ui,
                                bg='#10B981', fg='white',
                                font=("Segoe UI", 13, "bold"), width=20, height=1,
                                relief='flat', cursor='hand2')
        register_btn.pack(pady=5)
        self.security_label = tk.Label(form_frame, text="🔍 بررسی امنیت سیستم...",
                                      font=("Segoe UI", 9), bg=self.colors['bg'],
                                      fg=self.colors['accent'])
        self.security_label.pack(pady=(20, 0))
        self.check_system_security()

    def check_system_security(self):
        try:
            is_remote = check_remote_access()
            physical_kb, physical_mouse, details = check_physical_keyboard_mouse()
            if is_remote:
                self.security_label.config(
                    text="⚠️ هشدار: اتصال از راه دور شناسایی شد! ورود غیرفعال است.",
                    fg=self.colors['error_fg']
                )
                for widget in self.login_frame.winfo_children():
                    if isinstance(widget, tk.Button):
                        widget.config(state='disabled')
            elif not physical_kb:
                self.security_label.config(
                    text="⚠️ صفحه‌کلید فیزیکی تشخیص داده نشد. عملکرد محدود.",
                    fg='#F59E0B'
                )
            else:
                self.security_label.config(
                    text="✅ سیستم ایمن - دستگاه‌های فیزیکی تشخیص داده شدند",
                    fg=self.colors['success_fg']
                )
        except Exception as e:
            self.security_label.config(
                text=f"⚠️ بررسی امنیت با خطا مواجه شد: {str(e)}",
                fg=self.colors['error_fg']
            )

    def show_register_ui(self):
        self.login_frame.pack_forget()
        self.register_frame = tk.Frame(self.root, bg=self.colors['bg'])
        self.register_frame.pack(expand=True, fill='both')
        title_frame = tk.Frame(self.register_frame, bg=self.colors['title_bg'], height=100)
        title_frame.pack(fill='x', pady=(0, 30))
        title_frame.pack_propagate(False)
        tk.Label(title_frame, text="📝 ثبت‌نام کاربر جدید",
                font=("Segoe UI", 24, "bold"),
                bg=self.colors['title_bg'],
                fg=self.colors['title_fg']).pack(expand=True)
        form_frame = tk.Frame(self.register_frame, bg=self.colors['bg'])
        form_frame.pack(pady=30)
        tk.Label(form_frame, text="👤 انتخاب نام کاربری", font=("Segoe UI", 12),
                bg=self.colors['bg'], fg=self.colors['fg']).pack(anchor='w', pady=(0, 5))
        self.reg_username = tk.Entry(form_frame, font=("Segoe UI", 12),
                                     width=35, bg=self.colors['input_bg'],
                                     fg=self.colors['input_fg'],
                                     relief='solid', bd=1)
        self.reg_username.pack(pady=(0, 15))
        tk.Label(form_frame, text="🔒 انتخاب رمزعبور", font=("Segoe UI", 12),
                bg=self.colors['bg'], fg=self.colors['fg']).pack(anchor='w', pady=(0, 5))
        self.reg_password = tk.Entry(form_frame, font=("Segoe UI", 12),
                                     width=35, bg=self.colors['input_bg'],
                                     fg=self.colors['input_fg'], show="•",
                                     relief='solid', bd=1)
        self.reg_password.pack(pady=(0, 15))
        tk.Label(form_frame, text="🔒 تأیید رمزعبور", font=("Segoe UI", 12),
                bg=self.colors['bg'], fg=self.colors['fg']).pack(anchor='w', pady=(0, 5))
        self.reg_confirm = tk.Entry(form_frame, font=("Segoe UI", 12),
                                    width=35, bg=self.colors['input_bg'],
                                    fg=self.colors['input_fg'], show="•",
                                    relief='solid', bd=1)
        self.reg_confirm.pack(pady=(0, 25))
        btn_frame = tk.Frame(form_frame, bg=self.colors['bg'])
        btn_frame.pack()
        register_btn = tk.Button(btn_frame, text="✅ ثبت‌نام", command=self.register_user,
                                bg='#10B981', fg='white',
                                font=("Segoe UI", 13, "bold"), width=20, height=1,
                                relief='flat', cursor='hand2')
        register_btn.pack(pady=5)
        back_btn = tk.Button(btn_frame, text="← بازگشت به ورود", command=self.back_to_login,
                            bg='#6B7280', fg='white',
                            font=("Segoe UI", 13, "bold"), width=20, height=1,
                            relief='flat', cursor='hand2')
        back_btn.pack(pady=5)

    def register_user(self):
        username = self.reg_username.get().strip()
        password = self.reg_password.get()
        confirm = self.reg_confirm.get()
        if not username or not password:
            messagebox.showerror("خطا", "❌ تمام فیلدها الزامی هستند!")
            return
        if len(username) < 3:
            messagebox.showerror("خطا", "❌ نام کاربری باید حداقل ۳ کاراکتر باشد!")
            return
        if len(password) < 6:
            messagebox.showerror("خطا", "❌ رمزعبور باید حداقل ۶ کاراکتر باشد!")
            return
        if password != confirm:
            messagebox.showerror("خطا", "❌ رمزعبورها مطابقت ندارند!")
            return
        success, message = DatabaseManager.register_user(username, password)
        if success:
            messagebox.showinfo("موفقیت", f"✅ {message}\n\nلطفاً با حساب کاربری جدید وارد شوید.")
            self.back_to_login()
        else:
            messagebox.showerror("خطا", f"❌ {message}")

    def back_to_login(self):
        if hasattr(self, 'register_frame'):
            self.register_frame.destroy()
        self.setup_login_ui()

    def login(self):
        if check_remote_access():
            messagebox.showerror("هشدار امنیتی",
                               "🚫 اتصال از راه دور شناسایی شد!\n\n"
                               "به دلایل امنیتی، ورود فقط از صفحه‌کلید و ماوس فیزیکی مجاز است.\n"
                               "لطفاً به این دستگاه به‌صورت مستقیم متصل شوید.")
            return
        physical_kb, _, _ = check_physical_keyboard_mouse()
        if not physical_kb:
            response = messagebox.askyesno("هشدار امنیتی",
                                         "⚠️ صفحه‌کلید فیزیکی تشخیص داده نشد!\n\n"
                                         "این ممکن است یک اتصال از راه دور باشد.\n"
                                         "آیا همچنان می‌خواهید ادامه دهید؟")
            if not response:
                return
        username = self.username_entry.get().strip()
        password = self.password_entry.get()
        if not username or not password:
            messagebox.showerror("خطا", "❌ لطفاً نام کاربری و رمزعبور را وارد کنید!")
            return
        success, message = DatabaseManager.authenticate_user(username, password)
        if success:
            self.current_user = username
            session_data = f"{username}:{datetime.now().isoformat()}"
            self.session_signature = generate_digital_signature(session_data)
            self.login_frame.pack_forget()
            self.setup_main_ui()
            self.main_frame.pack(fill="both", expand=True)
            self.load_password_history()
        else:
            messagebox.showerror("ورود ناموفق", f"❌ {message}")

    def setup_main_ui(self):
        self.main_frame = tk.Frame(self.root, bg=self.colors['bg'])
        header_frame = tk.Frame(self.main_frame, bg=self.colors['title_bg'], height=80)
        header_frame.pack(fill='x')
        header_frame.pack_propagate(False)
        tk.Label(header_frame, text=f"🔐 خوش آمدید، {self.current_user}",
                font=("Segoe UI", 18, "bold"),
                bg=self.colors['title_bg'], fg=self.colors['title_fg']).pack(side='left', padx=25)
        theme_text = "🌙 تاریک" if self.current_theme == "light" else "☀️ روشن"
        self.theme_btn = tk.Button(header_frame, text=theme_text, command=self.toggle_theme,
                                   bg=self.colors['title_fg'], fg=self.colors['title_bg'],
                                   font=("Segoe UI", 10, "bold"), relief='flat',
                                   cursor='hand2', padx=15)
        self.theme_btn.pack(side='right', padx=10)
        logout_btn = tk.Button(header_frame, text="🚪 خروج", command=self.logout,
                              bg='#EF4444', fg='white',
                              font=("Segoe UI", 10, "bold"), relief='flat',
                              cursor='hand2', padx=15)
        logout_btn.pack(side='right', padx=5)
        canvas = tk.Canvas(self.main_frame, bg=self.colors['bg'], highlightthickness=0)
        scrollbar = tk.Scrollbar(self.main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=self.colors['bg'])
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", on_mousewheel)
        content = scrollable_frame

        # Security status
        security_frame = tk.LabelFrame(content, text="🛡️ وضعیت امنیتی",
                                       font=("Segoe UI", 12, "bold"),
                                       bg=self.colors['bg'], fg=self.colors['fg'],
                                       relief='solid', bd=1)
        security_frame.pack(fill='x', pady=15, padx=30)
        try:
            physical_kb, physical_mouse, details = check_physical_keyboard_mouse()
            status_text = ""
            if physical_kb:
                status_text += "✅ صفحه‌کلید فیزیکی: متصل\n"
            else:
                status_text += "⚠️ صفحه‌کلید فیزیکی: شناسایی نشد\n"
            if physical_mouse:
                status_text += "✅ ماوس فیزیکی: متصل\n"
            else:
                status_text += "⚠️ ماوس فیزیکی: شناسایی نشد\n"
            status_text += f"🔐 امضای نشست: {self.session_signature[:16]}..."
        except:
            status_text = "⚠️ بررسی امنیت در دسترس نیست"
        tk.Label(security_frame, text=status_text,
                font=("Consolas", 9), bg=self.colors['bg'],
                fg=self.colors['success_fg'] if '✅' in status_text else self.colors['error_fg'],
                justify='left').pack(padx=15, pady=10, anchor='w')

        # Length
        length_frame = tk.Frame(content, bg=self.colors['bg'])
        length_frame.pack(fill='x', pady=15, padx=30)
        tk.Label(length_frame, text="📏 طول رمزعبور", font=("Segoe UI", 13, "bold"),
                bg=self.colors['bg'], fg=self.colors['fg']).pack(anchor='w')
        self.length_var = tk.IntVar(value=12)
        length_slider = tk.Scale(length_frame, from_=6, to=32, orient='horizontal',
                                 variable=self.length_var, bg=self.colors['bg'],
                                 fg=self.colors['accent'], troughcolor=self.colors['accent_light'],
                                 sliderlength=20, length=500)
        length_slider.pack(pady=10)
        self.length_label = tk.Label(length_frame, text="12 کاراکتر",
                                    font=("Segoe UI", 11), bg=self.colors['bg'],
                                    fg=self.colors['accent'])
        self.length_label.pack()
        length_slider.configure(command=self.update_length_label)

        # Type
        type_frame = tk.LabelFrame(content, text="🔑 نوع رمزعبور",
                                   font=("Segoe UI", 12, "bold"),
                                   bg=self.colors['bg'], fg=self.colors['fg'],
                                   relief='solid', bd=1)
        type_frame.pack(fill='x', pady=15, padx=30)
        self.pwd_type = tk.StringVar(value="letters_numbers")
        types = [
            ("🔤 حروف + اعداد (پیش‌نهادی)", "letters_numbers"),
            ("🔢 فقط اعداد", "only_digits"),
            ("✨ حروف + اعداد + نمادها (امنیت بالا)", "with_symbols")
        ]
        for text, value in types:
            tk.Radiobutton(type_frame, text=text, variable=self.pwd_type, value=value,
                          bg=self.colors['bg'], fg=self.colors['fg'],
                          selectcolor=self.colors['accent_light'],
                          activebackground=self.colors['bg']).pack(anchor='w', padx=20, pady=8)

        # Generate
        gen_btn = tk.Button(content, text="🎲 تولید و رمزنگاری رمزعبور",
                           command=self.generate_and_display,
                           bg=self.colors['button_bg'], fg=self.colors['button_fg'],
                           font=("Segoe UI", 13, "bold"), height=2,
                           relief='flat', cursor='hand2')
        gen_btn.pack(fill='x', pady=20, padx=30)

        # Display
        display_frame = tk.LabelFrame(content, text="🔐 رمزعبور تولید شده",
                                      font=("Segoe UI", 12, "bold"),
                                      bg=self.colors['bg'], fg=self.colors['fg'],
                                      relief='solid', bd=1)
        display_frame.pack(fill='x', pady=15, padx=30)
        self.password_display = tk.Entry(display_frame, font=("Consolas", 13, "bold"),
                                        bg=self.colors['input_bg'], fg=self.colors['accent'],
                                        justify='center', state='readonly',
                                        relief='sunken', bd=2)
        self.password_display.pack(padx=15, pady=15, fill='x')
        tk.Label(display_frame, text="🔒 نسخه رمزنگاری شده:",
                font=("Segoe UI", 10, "bold"), bg=self.colors['bg'],
                fg=self.colors['fg']).pack(anchor='w', padx=15)
        self.encrypted_display = tk.Entry(display_frame, font=("Consolas", 10),
                                         bg=self.colors['input_bg'], fg=self.colors['error_fg'],
                                         justify='center', state='readonly',
                                         relief='sunken', bd=1)
        self.encrypted_display.pack(padx=15, pady=(0, 15), fill='x')
        copy_btn = tk.Button(display_frame, text="📋 کپی رمزعبور",
                            command=self.copy_to_clipboard,
                            bg=self.colors['button_bg'], fg=self.colors['button_fg'],
                            font=("Segoe UI", 11, "bold"), relief='flat',
                            cursor='hand2', height=1)
        copy_btn.pack(pady=(0, 15))

        # History
        history_frame = tk.LabelFrame(content, text="📜 تاریخچه رمزعبورها (ذخیره‌شده به‌صورت رمزنگاری)",
                                      font=("Segoe UI", 12, "bold"),
                                      bg=self.colors['bg'], fg=self.colors['fg'],
                                      relief='solid', bd=1)
        history_frame.pack(fill='both', expand=True, pady=15, padx=30)
        list_frame = tk.Frame(history_frame, bg=self.colors['bg'])
        list_frame.pack(fill='both', expand=True, padx=10, pady=10)
        history_scrollbar = tk.Scrollbar(list_frame)
        history_scrollbar.pack(side='right', fill='y')
        self.passwords_listbox = tk.Listbox(list_frame, font=("Consolas", 9),
                                           bg=self.colors['input_bg'], fg=self.colors['fg'],
                                           yscrollcommand=history_scrollbar.set,
                                           selectbackground=self.colors['accent'],
                                           relief='flat', height=8)
        self.passwords_listbox.pack(side='left', fill='both', expand=True)
        history_scrollbar.config(command=self.passwords_listbox.yview)

        # Bottom buttons
        btn_frame = tk.Frame(content, bg=self.colors['bg'])
        btn_frame.pack(pady=20, padx=30)
        clear_btn = tk.Button(btn_frame, text="🗑️ پاک کردن تاریخچه", command=self.clear_history,
                             bg='#E74C3C', fg='white', font=("Segoe UI", 11, "bold"),
                             relief='flat', padx=25, pady=10, cursor='hand2')
        clear_btn.pack(side='left', padx=10, expand=True, fill='x')
        exit_btn = tk.Button(btn_frame, text="🚪 خروج از برنامه", command=self.exit_app,
                            bg='#95A5A6', fg='white', font=("Segoe UI", 11, "bold"),
                            relief='flat', padx=25, pady=10, cursor='hand2')
        exit_btn.pack(side='left', padx=10, expand=True, fill='x')
        self.update_password_list()

    def load_password_history(self):
        if not self.current_user:
            return
        history = DatabaseManager.get_password_history(self.current_user)
        self.stored_passwords = history
        self.update_password_list()

    def update_password_list(self):
        self.passwords_listbox.delete(0, tk.END)
        if self.stored_passwords:
            for i, entry in enumerate(self.stored_passwords, 1):
                decrypted = entry['decrypted']
                pwd_type = entry['type']
                created = entry['created_at'][:19]
                display_text = f"{i:2}. [{pwd_type[:15]:15}] {decrypted[:30]}... ({created})"
                self.passwords_listbox.insert(tk.END, display_text)
        else:
            self.passwords_listbox.insert(tk.END, "  ~ هنوز رمزعبوری تولید نشده است ~")

    def toggle_theme(self):
        if self.current_theme == "light":
            self.current_theme = "dark"
            self.colors = self.dark_colors
        else:
            self.current_theme = "light"
            self.colors = self.light_colors
        self.main_frame.destroy()
        self.setup_main_ui()
        self.main_frame.pack(fill="both", expand=True)

    def update_length_label(self, value):
        self.length_label.config(text=f"{int(float(value))} کاراکتر")

    def generate_password(self, length, only_digits=False, include_symbols=False):
        if only_digits:
            return ''.join(random.choices(string.digits, k=length))
        else:
            characters = string.ascii_letters + string.digits
            if include_symbols:
                characters += string.punctuation
            return ''.join(random.choices(characters, k=length))

    def generate_and_display(self):
        if not self.current_user:
            messagebox.showerror("خطا", "❌ هیچ کاربری وارد نشده است!")
            return
        physical_kb, _, _ = check_physical_keyboard_mouse()
        if not physical_kb:
            if not messagebox.askyesno("هشدار", "صفحه‌کلید فیزیکی تشخیص داده نشد. ادامه می‌دهید؟"):
                return
        length = self.length_var.get()
        pwd_type = self.pwd_type.get()
        use_digits_only = (pwd_type == "only_digits")
        use_symbols = (pwd_type == "with_symbols")
        password = self.generate_password(length, use_digits_only, use_symbols)
        self.password_display.config(state='normal')
        self.password_display.delete(0, tk.END)
        self.password_display.insert(0, password)
        self.password_display.config(state='readonly')
        encrypted = encrypt_password(password)
        self.encrypted_display.config(state='normal')
        self.encrypted_display.delete(0, tk.END)
        self.encrypted_display.insert(0, encrypted[:50] + "..." if len(encrypted) > 50 else encrypted)
        self.encrypted_display.config(state='readonly')
        success, message = DatabaseManager.save_password(
            self.current_user, password, pwd_type, length
        )
        if success:
            self.load_password_history()
            messagebox.showinfo("موفقیت", f"✅ رمزعبور تولید و رمزنگاری شد!\n\n"
                                f"رمزعبور: {password}\n"
                                f"به‌صورت ایمن در پایگاه داده ذخیره شد.")
        else:
            messagebox.showerror("خطا", f"❌ ذخیره‌سازی ناموفق: {message}")

    def copy_to_clipboard(self):
        password = self.password_display.get()
        if password:
            self.root.clipboard_clear()
            self.root.clipboard_append(password)
            messagebox.showinfo("کپی شد!", "📋 رمزعبور در کلیپ‌بورد کپی شد!")
        else:
            messagebox.showwarning("هشدار", "⚠️ ابتدا یک رمزعبور تولید کنید!")

    def clear_history(self):
        if not self.current_user:
            return
        if messagebox.askyesno("تأیید پاک کردن",
                              "⚠️ آیا مطمئن هستید که می‌خواهید تمام تاریخچه را پاک کنید؟\n\n"
                              "این عمل قابل بازگشت نیست!"):
            success, message = DatabaseManager.clear_password_history(self.current_user)
            if success:
                self.stored_passwords = []
                self.update_password_list()
                messagebox.showinfo("پاک شد", "✅ تاریخچه رمزعبور با موفقیت پاک شد!")
            else:
                messagebox.showerror("خطا", f"❌ {message}")

    def logout(self):
        self.current_user = None
        self.stored_passwords = []
        self.main_frame.destroy()
        self.setup_login_ui()

    def exit_app(self):
        if messagebox.askyesno("خروج", "آیا مطمئن هستید که می‌خواهید خارج شوید؟"):
            self.root.quit()
            self.root.destroy()

if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = ModernPasswordGenerator(root)
        root.mainloop()
    except Exception as e:
        print(f"خطای بحرانی: {e}")
        import traceback
        traceback.print_exc()
        input("برای خروج Enter را فشار دهید...")
