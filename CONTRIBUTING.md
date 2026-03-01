# Contributing to DomiChess2

First off, thank you for considering contributing to DomiChess2! It's people like you that make the open-source community such an amazing place to learn, inspire, and create.

We welcome contributions of all forms: bug fixes, new features, documentation improvements, or even just reporting issues.

## 🛠️ Prerequisites & Tooling

To contribute to this project, you will need to install a few tools. We rely on modern workflows to keep things fast and simple.

### 1. Git
You likely already have this, but if not, download and install it from [git-scm.com](https://git-scm.com/downloads).

### 2. GitHub CLI (`gh`)
We use the GitHub CLI to streamline working with repositories and Pull Requests directly from the terminal.
*   **Download:** [cli.github.com](https://cli.github.com/)
*   **Setup:** Once installed, run the following command in your terminal to authenticate with your GitHub account:
    ```bash
    gh auth login
    ```

### 3. uv (Python Package Manager)
We use `uv` (by Astral) for extremely fast dependency management and virtual environment creation.
*   **Installation:**
    *   **Windows (PowerShell):**
        ```powershell
        powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
        ```
    *   **macOS / Linux:**
        ```bash
        curl -LsSf https://astral.sh/uv/install.sh | sh
        ```
*   **Verify:** Ensure it's installed by running `uv --version`.

---

## 🚀 Getting Started

Follow these steps to set up your local development environment.

### 1. Fork and Clone the Repository
Using the GitHub CLI, you can fork the repository and clone it to your machine in one command:

```bash
gh repo fork devfred78/DomiChess2 --clone
cd DomiChess2
```

### 2. Set Up the Virtual Environment
Use `uv` to create a virtual environment and install the project in "editable" mode. This allows you to modify the code and see changes immediately without reinstalling.

**Windows:**
```powershell
uv venv
.venv\Scripts\activate
uv pip install -e .[dev]
```

**macOS / Linux:**
```bash
uv venv
source .venv/bin/activate
uv pip install -e .[dev]
```

> **Note:** The `[dev]` flag ensures you also install development tools like PyInstaller.

---

## 💻 Development Workflow

### 1. Create a New Branch
Always create a new branch for your work. Do not commit directly to `main`.

```bash
git checkout -b feature/my-awesome-feature
# or for a bug fix
git checkout -b fix/startup-crash
```

### 2. Make Your Changes
Write your code!
*   **Code Style:** Try to keep the code consistent with the existing style.
*   **Tests:** If you add a new feature, please add a corresponding test in the `tests/` folder.

### 3. Run Tests
Before submitting, ensure that your changes didn't break anything.

```bash
python -m unittest discover tests
```

---

## ​​​​​​​📥 Submitting a Pull Request

Once your code is ready and tested, follow these steps to submit it.

### 1. Commit Your Changes
Write a clear and concise commit message.

```bash
git add .
git commit -m "Add feature: Save game to PGN format"
```

### 2. Push to Your Fork
Push your branch to your forked repository on GitHub.

```bash
git push -u origin feature/my-awesome-feature
```

### 3. Create a Pull Request (PR)
You can create the Pull Request directly from your terminal using the GitHub CLI. This will open a browser window (or a text editor) to let you fill in the title and description.

```bash
gh pr create
```

*   **Title:** A short summary of the change.
*   **Body:** Describe what you changed and why. If it fixes an issue, link to it (e.g., "Fixes #42").
*   **Review:** Submit the PR. We will review it as soon as possible!

---

Thank you for your contribution! ♟️
