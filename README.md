# 💸 Notion Finance Tracker Bot

[![Version](https://img.shields.io/badge/version-1.2.0-blue.svg)](https://github.com/MikeSydo/notion-finance-tracker/releases)
[![License: Proprietary](https://img.shields.io/badge/License-Proprietary-red.svg)](#license)

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
    git clone https://github.com/MikeSydo/notion-finance-tracker.git
    cd notion-finance-tracker
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

## 📄 License

Copyright (c) 2026 Mykhailo Sydoruk (MikeSydo). All Rights Reserved.

This software and associated documentation files are proprietary. Unauthorized copying, modification, distribution, or use of this software, via any medium, is strictly prohibited.
