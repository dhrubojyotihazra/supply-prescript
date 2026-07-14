# Developer & Git Collaboration Guide

Welcome to the **SupplyPrescript** project! This guide covers the essential Git commands and workflow guidelines for all team developers.

---

## 1. First-Time Setup

Before you start, make sure you have Git installed and configured with your name and email:

```bash
# Set your commit name
git config --global user.name "Your Name"

# Set your commit email (must match your GitHub email)
git config --global user.email "your.email@example.com"
```

---

## 2. Clone the Repository

Clone the project to your local computer:

```bash
# Clone the repository
git clone https://github.com/dhrubojyotihazra/supply-prescript.git

# Move into the project directory
cd supply-prescript
```

---

## 3. Recommended Developer Workflow

To avoid conflicts and keep the history clean, follow these steps when working on a new feature:

### Step A: Pull Latest Changes
Always start by getting the latest code from the remote `main` branch:
```bash
git checkout main
git pull origin main
```

### Step B: Create a Feature Branch
Create a new branch for your task:
```bash
# Format: feature/short-description
git checkout -b feature/add-database-schema
```

### Step C: Code and Commit
Make your changes locally, then stage and commit them:
```bash
# Check status of modified files
git status

# Stage all modified and new files
git add .

# Commit with a descriptive message
git commit -m "feat: implement database write-back schema"
```

### Step D: Push Your Branch to GitHub
Push your local branch to the remote repository:
```bash
git push -u origin feature/add-database-schema
```

### Step E: Open a Pull Request (PR)
1. Go to the repository page on [GitHub](https://github.com/dhrubojyotihazra/supply-prescript).
2. You will see a prompt saying **"Compare & pull request"** for your recently pushed branch. Click it.
3. Review your changes and click **Create pull request**.
4. Once reviewed/approved, click **Merge pull request** to merge your code into the `main` branch.

---

## 4. Alternative: Directly Committing to Main (Quick Updates)

If your team agrees to push directly to the `main` branch:

```bash
# 1. Pull latest code to avoid conflicts
git pull origin main

# 2. Make your edits

# 3. Stage and commit
git add .
git commit -m "docs: update readme instructions"

# 4. Push directly to main
git push origin main
```

---

## 5. Resolving Conflicts (If They Occur)

If someone else pushed changes to `main` while you were working on the same file:

```bash
# 1. Pull latest changes
git pull origin main

# 2. Git will flag conflicts in your editor. Open the files and resolve them.
# 3. Once resolved, stage the files:
git add <conflicted-file>

# 4. Complete the merge or commit:
git commit -m "merge: resolve conflicts with main"

# 5. Push to GitHub:
git push
```
