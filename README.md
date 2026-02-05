# Security Audit Tool

A Python-based GUI application developed using **PyQt5** and **Paramiko** to
perform **authentication security audits** in controlled and authorized environments.

This tool is designed to help students and security practitioners understand
authentication mechanisms and evaluate password strength during security assessments.

> **Educational & Authorized Use Only**  
> This application must be used **only on systems you own or have explicit permission to test**.
> Unauthorized access to computer systems is illegal.

---

## Key Features

- Secure user login and registration system  
- Password protection using **SHA-256 hashing**
- Authentication testing using controlled password lists
- Multithreaded execution with **QThread** for responsiveness
- Real-time audit logs and progress visualization
- Dark-themed, cybersecurity-inspired user interface

---

## Technology Stack

- **Python 3.x**
- **PyQt5** – Graphical User Interface
- **Paramiko** – Secure remote connection handling
- **JSON** – User data persistence
- **SHA-256** – Secure password hashing
- **Multithreading** – Efficient execution

---

##  How to Run the Application

```bash
git clone https://github.com/your-username/security-audit-tool.git
cd security-audit-tool
pip install -r requirements.txt
python src/main.py
