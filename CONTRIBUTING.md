# 🤝 Contributing to Notion Finance Tracker

First off, thank you for considering contributing to the Notion Finance Tracker! Your help is highly appreciated.

Since this project is open-source and licensed under the **MIT License**, you're more than welcome to submit pull requests to fix bugs, add new features, or improve the documentation. By contributing, you agree that your work will be licensed under the same MIT terms.

## 🛠 Getting Started

### 1. Fork the Repository
Fork the original repository to your own GitHub account, then clone it locally:

```bash
git clone https://github.com/YOUR_USERNAME/notion-finance-tracker.git
cd notion-finance-tracker
```

### 2. Set Up Your Environment
Please refer to the **Development Setup** section in the [README.md](README.md). Make sure you configure your `.env` correctly.

### 3. TDD (Test-Driven Development) Methodology - ⚠️ IMPORTANT
This project strictly enforces **Test-Driven Development (TDD)** for all business logic, especially for any code inside the `services/` directory. 

Whenever you refactor or add new features, you **MUST** follow these steps:
1. **Update Tests First**: _Before_ modifying any service logic, update or create corresponding tests in the `tests/` directory.
2. **Run Tests (Expect Failure)**: Run `pytest tests/ -v` to confirm the new/updated tests fail.
3. **Refactor/Implement Logic**: Modify the codebase to make the tests pass.
4. **Run Tests Again**: Ensure the test suite passes successfully. Do not rewrite tests just to bypass failures!

### 4. Code Style & Commit Guidelines
- Use modern Python features (type hinting, etc.).
- Ensure your code passes all linters.
- When committing, write clear and descriptive commit messages.

### 5. Create a Pull Request
1. Push your changes to your fork.
2. Open a Pull Request from your branch to the `main` branch of this repository.
3. Fill out the PR template correctly.

## 🐛 Found a Bug or Have a Feature Idea?
Please use the provided Issue Templates in the GitHub repository's "Issues" tab. Provide as much detail as possible so we can reproduce and fix the bug, or understand your proposal!

Thank you again for helping out! 🎉
