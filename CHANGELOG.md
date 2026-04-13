# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [v0.3.2] - 2026-04-13

### Fixed
- **🧾 Receipt Parsing Logic**: Resolved a bug where discounts (Знижки) and taxes (ПДВ) were treated as regular products. Added item classification to filter these out of the UI table while maintaining mathematical total accuracy.
- **🌐 Localization Fix**: Resolved a critical issue where the "AI Busy" message was displayed as a raw technical key (`rcp_gemini_busy`) instead of translated text.
- **✨ Sync Locales**: Synchronized Ukrainian and English localization files to ensure consistent coverage of all bot features.

---

## [v0.3.1] - 2026-04-13

### Fixed
- **🏷️ Docker Tagging**: Fixed `invalid reference format` error during deployment by ensuring repository names are consistently lowercased across all workflows.
- **🛠️ Infrastructure Fix**: Transitioned to a custom `DOCKER_IMAGE_NAME` variable to avoid conflicts with default internal GitHub variables.

---

## [v0.3.0] - 2026-04-13

This major infrastructure release marks the transition to the **NotiFinBot** brand and a fully integrated GitHub-native ecosystem.

### Added
- **🛡️ Security Policy**: Added `SECURITY.md` to establish a clear process for responsible vulnerability disclosure.
- **🤖 Dependabot Integration**: Enabled automated security and dependency monitoring for Python packages and GitHub Actions.
 
### Changed
- **✨ Rebranding**: Project officially renamed to **NotiFinBot**. Container names, database references, and documentation updated to reflect the new identity.
- **📦 Registry Migration**: Fully migrated from Docker Hub to **GitHub Container Registry (GHCR)**. Switched to `GITHUB_TOKEN` for more secure, integrated build authentication.
- **🛠️ Infrastructure Modernization**: Updated all GitHub Actions to their latest versions and optimized CI logic for faster feedback loops.
 
---

## [v0.2.1] - 2026-04-13

This release focuses on localization polish, codebase standardization, and test structure improvements for the upcoming public repository launch.

### Added
- **🌐 Localized Menus**: Telegram bot command menus are now fully localized and respond automatically to the user's Telegram client language settings (English/Ukrainian).

### Changed
- **⚙️ Version Control**: Centralized versioning (`VERSION`) and changelog routing (`CHANGELOG_URL`) into `config.py` as the single source of truth, removing them from `.env` files.
- **📁 Test Architecture**: Cleaned up the repository root by relocating mock files to `tests/assets/`, aligning with open-source testing best practices.

### Fixed
- **🐛 Validation Error**: Fixed a bug in `main.py` where missing command descriptions caused Pydantic validation errors on launch.
- **🗣️ Language Fallback**: Resolved annoying warning logs by properly defaulting to English (`en`) when a user's language code is `None`.

---

## [v0.2.0] - 2026-04-12

The core focus of this release is a complete overhaul of the Notion connection logic, making the bot significantly smarter and more reliable during the onboarding process.

### Fixed
- Resolved a critical bug where the bot could "mix up" databases if you granted access to multiple identical Notion templates.
- The bot now automatically groups all discovered objects by their parent page and selects the most complete "project" group. This ensures that your expenses, accounts, and statistics always remain linked within the same workspace.

---

## [v0.1.1] - 2026-04-12

This release transforms the bot's analytics into a lightning-fast tool and fixes critical interface shortcomings.

### Changed
- **🚀 Reworked Analytics**: We have replaced static charts with a direct link to your **Stats** section in Notion. Access your financial dashboards instantly and leverage Notion's native visualization tools.

### Fixed
- **⌨️ Fixed Expense Keyboards**: Resolved the pagination issue where the keyboard would reset to the first page when selecting items. Your navigation state is now preserved.

---

## [v0.1.0] - 2026-04-09

### Added
- **Brainstorming AI & Receipt Analysis**: Distinguishing "Analysis Error" from "Notion Saving Error" for clearer user communication.

### Fixed
- **Retry Mechanism**: The bot now automatically retries up to 3 times with exponential backoff if Google's servers are busy.

---

## [v0.0.1] - 2026-04-09

In this update, we focused on AI stability and data protection to make your finance tracking even more seamless.

### Added
- **🧠 Smarter Receipt Recognition**: Optimized AI logic (Gemini) to be more flexible. Whether your photo is taken at an angle, in low light, or on a dark background, the bot is now far more accurate.
- **🛡️ Automated Storage Cleanup**: When you delete a group expense via the bot, the associated receipt photo is automatically permanently deleted from cloud storage.

### Changed
- **⚡ Performance Optimization**: Faster image processing and more reliable metadata extraction for your expenses.

---

## [v0.0.0] - 2026-04-09

### Added
- Initial launch of the NotiFinBot.
- Basic receipt photo parsing and Notion database integration.
- Support for multiple accounts and categories.
- Secure OAuth 2.0 authentication flow.

---

## [v0.0.0-beta] - 2026-04-08

### Changed
- Initial beta testing phase. Focused on Notion integration stability and database discovery refinement.

---

## [v0.0.0-alpha] - 2026-04-07

### Added
- Early alpha prototype. Core architecture setup and first Gemini API connection for image analysis.
