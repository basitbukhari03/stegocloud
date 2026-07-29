# StegoCloud — Steganography-Based Cloud Data Protection System

> **University Hackathon Project** — A two-layer secure cloud storage system combining AES-256 encryption with LSB steganography, protected by multi-factor authentication.

---

## 🔐 What Is StegoCloud?

StegoCloud hides your secret data inside ordinary-looking images using two independent layers of protection:

| Layer | Technique | What It Does |
|-------|-----------|-------------|
| **1** | AES-256-CBC Encryption | Makes the message unreadable without the password |
| **2** | LSB Steganography | Hides the encrypted data inside image pixels — invisible to the eye |

Even if an attacker gets the image, they see a normal photo. Even if they extract the hidden bits, they only get AES-encrypted ciphertext.

---

## ✨ Features

- 🔒 **AES-256-CBC Encryption** via PyCryptodome — SHA-256 key derivation
- 🖼️ **LSB Steganography** — manual implementation using Pillow only
- 📱 **TOTP Multi-Factor Authentication** — Google Authenticator compatible
- 👤 **Role-Based Access Control** — Admin and User roles
- 🛡️ **Brute-Force Protection** — account lockout after 5 failed attempts
- 📊 **Dashboard with Chart.js** — activity charts, file stats
- 📋 **Full Audit Logging** — every action logged to SQLite + rotating log files
- 🌑 **Professional Dark UI** — glassmorphism, animations, glowing effects
- 🔍 **Filterable Audit Logs** — filter by action type
- 🗑️ **File Management** — upload, download, delete stego images
- 🔐 **CSRF Protection** — Flask-WTF on all forms
- 📁 **Simulated Cloud Storage** — `cloud_storage/` folder acts as cloud bucket

---

## 📂 Project Structure

```
stegocloud/
├── app.py                  ← Flask app factory + all route blueprints
├── config.py               ← Configuration (DB, session, uploads)
├── models.py               ← SQLAlchemy models (User, StegoFile, AuditLog)
├── auth.py                 ← Auth blueprint (register, login, MFA, logout)
├── encryption.py           ← AES-256-CBC encrypt / decrypt
├── steganography.py        ← LSB hide / extract / capacity
├── logger.py               ← Audit log helper + rotating file logger
│
├── templates/
│   ├── base.html           ← Dark sidebar layout
│   ├── index.html          ← Landing page
│   ├── login.html          ← Login (step 1)
│   ├── register.html       ← Registration + password strength meter
│   ├── setup_mfa.html      ← QR code + manual secret
│   ├── verify_mfa.html     ← TOTP input with countdown ring
│   ├── dashboard.html      ← Charts + stats + recent activity
│   ├── hide_data.html      ← Embed secret in image
│   ├── extract_data.html   ← Extract & decrypt hidden data
│   ├── my_files.html       ← Manage stored stego images
│   ├── logs.html           ← Filterable audit log table
│   └── admin.html          ← Admin panel (users + global logs)
│
├── static/
│   ├── css/style.css       ← Full dark theme CSS
│   └── js/main.js          ← Sidebar, animations, utilities
│
├── cloud_storage/          ← Where stego images are saved
├── logs/                   ← Rotating file logs
│
├── test_steganography.py   ← Stego hide/extract roundtrip tests
├── demo_encryption.py      ← AES-256 encrypt/decrypt demo
└── requirements.txt
```

---

## 🚀 Installation & Setup

### 1. Clone / navigate to project
```bash
cd stegocloud
```

### 2. Create a virtual environment (recommended)
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the application
```bash
python app.py
```

The app starts at **http://localhost:5000**

> Database is auto-created on first run. Demo users are seeded automatically.

---


## 🖥️ How to Use

### Hiding Data
1. Sign in → Dashboard → **Hide Data**
2. Upload any PNG or JPG image (larger = more capacity)
3. Type your secret message
4. Enter an AES-256 encryption password
5. Click **Encrypt & Hide** — download the stego image

### Extracting Data
1. Sign in → **Extract Data**
2. Upload the stego image
3. Enter the same password used during hiding
4. The original message is revealed

---

## 🧪 Running Tests

```bash
# Test steganography (hide/extract roundtrip)
python test_steganography.py

# Test AES-256 encryption
python demo_encryption.py
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.10+ / Flask 2.3 |
| ORM | SQLAlchemy + SQLite |
| Auth | Flask-Login + Flask-Bcrypt |
| MFA | PyOTP (TOTP / RFC 6238) |
| Encryption | PyCryptodome AES-256-CBC |
| Steganography | Pillow (LSB, manual) |
| Frontend | Bootstrap 5 + Vanilla CSS + Chart.js |
| Forms/CSRF | Flask-WTF |
| QR Code | qrcode library |
| Logging | Python logging (RotatingFileHandler) |

---

## 🔒 Security Features

- CSRF protection on every form (Flask-WTF)
- SQL injection prevention via SQLAlchemy ORM
- XSS prevention via Jinja2 auto-escaping
- Brute-force lockout (5 attempts → 15 min lock)
- Secure HTTP headers (X-Frame-Options, X-XSS-Protection)
- File type validation (extension + MIME)
- Session timeout (30 minutes)
- Password complexity enforcement
- Full audit trail in SQLite + log files
- Passwords hashed with bcrypt

---

## 📸 Screenshots

> *(Add screenshots of Dashboard, Hide Data, and Extract Data pages here)*

---

## 📄 License

Built for educational/hackathon purposes. MIT License.
