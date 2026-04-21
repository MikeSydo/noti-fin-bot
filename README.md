# 💸 NotiFinBot

[![Version](https://img.shields.io/badge/version-0.3.4-blue.svg)](https://github.com/MikeSydo/noti-fin-bot/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

A powerful Telegram bot designed to seamlessly track your personal and group finances directly in **Notion**. Featuring AI-powered receipt parsing, automatic database discovery, and multi-language support.

---

## ✨ Key Features

-   **🔗 Seamless Notion Integration**: Connect your Notion workspace via OAuth 2.0 with automatic database discovery and setup.
-   **🤖 AI Receipt Parsing**: Simply send a photo or PDF of a receipt, and Google **Gemini AI** will extract store names, items, prices, and categories automatically.
-   **📈 Real-time Analytics**: Quick access to your financial statistics and trend charts directly in Notion.
-   **👥 Group Expenses**: Track shared spending and link individual expenses to group records.
-   **🌐 Multilingual**: Full support for **English** and **Ukrainian**.
-   **☁️ Secure Storage**: Receipts are securely stored in **AWS S3** and linked to your Notion entries.
-   **🛠️ Robust Architecture**: Built with `aiogram 3.x`, `SQLAlchemy 2.0`, and `Pydantic 2.x`.

---

## 🚀 Quick Start (Docker)

The easiest way to get the bot running is using Docker.

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/MikeSydo/noti-fin-bot.git
    cd noti-fin-bot
    ```

2.  **Configure environment variables**:
    Copy `.env.example` to `.env` and fill in your credentials (see [Configuration](#configuration)).
    ```bash
    cp .env.example .env
    ```

3.  **Run with Docker Compose**:
    ```bash
    docker-compose up -d
    ```

---

## 🛠️ Development Setup

If you want to run the bot locally for development:

1.  **Create a virtual environment**:
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Windows: .venv\Scripts\activate
    ```

2.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Apply database migrations**:
    ```bash
    alembic upgrade head
    ```

4.  **Start the bot**:
    ```bash
    python main.py
    ```

---

## ⚙️ Configuration

Your `.env` file must contain the following keys:

### Essential
- `TELEGRAM_BOT_TOKEN`: Your bot token from [@BotFather](https://t.me/botfather).
- `GEMINI_API_KEY`: API key from [Google AI Studio](https://aistudio.google.com/) for receipt parsing.
- `DATABASE_URL`: PostgreSQL connection string (e.g., `postgresql+asyncpg://user:pass@localhost/dbname`).
- `FERNET_KEY`: Key for encrypting Notion tokens. Generate one: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`.

### Notion OAuth
- `NOTION_CLIENT_ID`: From [Notion Developers](https://www.notion.so/my-integrations).
- `NOTION_CLIENT_SECRET`: Your Notion integration secret.
- `NOTION_REDIRECT_URI`: Should match your set callback (e.g., `https://your-domain.com/auth/callback`).

### AWS S3 (Receipt Storage)
- `AWS_REGION`, `AWS_S3_BUCKET_NAME`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`.

---

## 📖 Usage Guide

- `/start` - Open the main menu.
- `/connect` - Link your Notion workspace.
- `/disconnect` - Revoke bot access to Notion.
- `/help` - View help information.
- `/version` - Check current bot version and release notes.

**Tip**: Just send a photo of any receipt to the bot to start the automatic parsing flow!

---

## 🏗️ Technical Stack

- **Framework**: [aiogram 3.x](https://docs.aiogram.dev/) (Asynchronous Telegram Bot API)
- **Database**: [PostgreSQL](https://www.postgresql.org/) with [SQLAlchemy 2.0](https://www.sqlalchemy.org/)
- **AI**: [Google Gemini Pro Vision](https://deepmind.google/technologies/gemini/)
- **Integration**: [Notion API](https://developers.notion.com/)
- **Migrations**: [Alembic](https://alembic.sqlalchemy.org/)
- **Deployment**: [Docker](https://www.docker.com/) & [Caddy](https://caddyserver.com/)

---

## 🌍 Environment Management

The bot supports two environments: `prod` (default) and `dev`.

- **`prod`**: Processes look for an `.env` file. Used for the live bot on DigitalOcean.
- **`dev`**: Processes look for an `.env.dev` file. Used for local development and testing.

### How to Switch
Set the `ENV` environment variable before running the bot:

**Windows (PowerShell):**
```powershell
$env:ENV="dev"; python main.py
```

**Linux/macOS:**
```bash
ENV=dev python main.py
```

> [!NOTE]
> Currently, the project only supports `dev` and `prod` stages. We do not have a separate `staging` environment yet as it would require additional infrastructure (droplets).

---

## ☁️ Infrastructure & Deployment

This project is professionally hosted and managed using modern cloud infrastructure:

-   **Hosting**: The production environment is deployed on **DigitalOcean** (Linux Droplets) for optimal performance and uptime.
-   **CI/CD Pipeline**: Automated deployment via **GitHub Actions**. Every update to the `master` branch triggers high-speed testing, linting, and a new container build.
-   **Containerization**: High-reliability images are stored in **GitHub Container Registry (GHCR)**, ensuring identical environments from development to production.
-   **Reverse Proxy**: [Caddy](https://caddyserver.com/) handles all traffic with automatic HTTPS (Let's Encrypt), providing secure encryption out of the box.

---

## 🤝 Contributing

We welcome contributions from the community! If you'd like to help improve this project, please read our [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on how to fork the repository, set up your development environment, and submit a pull request.

---

## 📄 License

This project is open-source and licensed under the **MIT License**.

You are free to use, modify, and distribute this software for any purpose, including commercial use, provided that the original copyright notice and license are included.

For more details, see the [LICENSE](LICENSE) file.
