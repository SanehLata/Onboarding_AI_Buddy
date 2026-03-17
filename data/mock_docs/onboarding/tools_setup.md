# Developer Tools Setup Guide

**Last Updated:** January 2025
**Owner:** Platform Engineering
**Tags:** onboarding, tools, setup, environment, developer-experience

---

## Overview

This guide walks you through setting up your complete local development environment. Follow the steps in order. Estimated time: 2 to 3 hours on a new machine.

---

## Prerequisites

- Corporate laptop with macOS 13+ or Ubuntu 22.04+
- Corporate GitHub account provisioned (check your email for the invite)
- VPN access configured — see `vpn_access.md`

---

## 1. Core Tools

### Homebrew (macOS only)
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### Git
```bash
# macOS
brew install git

# Ubuntu
sudo apt-get install git
```

Configure Git with your corporate identity:
```bash
git config --global user.name "Your Name"
git config --global user.email "your.name@techcorp.com"
git config --global core.editor "vim"
```

### GitHub CLI
```bash
brew install gh   # macOS
sudo apt install gh   # Ubuntu

gh auth login
# Select: GitHub.com → HTTPS → Yes → Login with a web browser
```

---

## 2. Python Environment

TechCorp standardises on Python 3.11. Do not use system Python.

```bash
# Install pyenv
brew install pyenv   # macOS
curl https://pyenv.run | bash   # Ubuntu

# Add to your shell profile (~/.zshrc or ~/.bashrc)
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"

# Install Python 3.11
pyenv install 3.11.7
pyenv global 3.11.7

# Verify
python --version   # Should show Python 3.11.7
```

### Poetry (Dependency Management)
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

---

## 3. Docker & Containers

```bash
# macOS — download Docker Desktop
# https://www.docker.com/products/docker-desktop

# Ubuntu
sudo apt-get install docker-ce docker-ce-cli containerd.io
sudo usermod -aG docker $USER
```

Verify Docker is running:
```bash
docker run hello-world
```

---

## 4. Kubernetes Tools

```bash
# kubectl
brew install kubectl   # macOS
sudo apt-get install kubectl   # Ubuntu

# Configure cluster access (requires VPN)
aws eks update-kubeconfig --region eu-west-1 --name techcorp-dev

# Verify
kubectl get nodes
```

---

## 5. AWS CLI

```bash
brew install awscli   # macOS
sudo apt install awscli   # Ubuntu

# Configure with your developer credentials
aws configure
# Access Key: (from IT portal at accounts.techcorp.com)
# Secret Key: (from IT portal)
# Default region: eu-west-1
# Default output: json
```

---

## 6. IDE Setup

### VS Code (Recommended)
Download from `https://code.visualstudio.com`

Required extensions:
```
ms-python.python
ms-python.black-formatter
ms-azuretools.vscode-docker
hashicorp.terraform
eamodio.gitlens
GitHub.copilot
```

Install all at once:
```bash
code --install-extension ms-python.python
code --install-extension ms-python.black-formatter
code --install-extension ms-azuretools.vscode-docker
code --install-extension hashicorp.terraform
code --install-extension eamodio.gitlens
code --install-extension GitHub.copilot
```

### IntelliJ IDEA (Java teams)
Licensed via JetBrains — request a licence through ServiceNow using the `SOFTWARE_REQUEST` ticket type.

---

## 7. Pre-commit Hooks

All repos use pre-commit hooks for linting and formatting:
```bash
pip install pre-commit
pre-commit install   # Run inside each repo after cloning
```

---

## 8. Environment Variables

Never hardcode credentials. Use a `.env` file locally:
```bash
# Copy the example file from the repo
cp .env.example .env
# Fill in your values — ask your manager for the dev credentials
```

The `.env` file is in `.gitignore` — never commit it.

---

## 9. Verify Your Setup

Run this checklist to confirm everything is working:
```bash
python --version       # 3.11.x
docker --version       # 24.x or higher
kubectl version        # connects to dev cluster
aws sts get-caller-identity  # returns your AWS account
gh auth status         # authenticated to GitHub
```

---

## Common Setup Issues

| Problem | Solution |
|---|---|
| `kubectl` cannot connect | Check VPN is connected |
| AWS credentials invalid | Re-generate from IT portal |
| Docker permission denied (Ubuntu) | Log out and back in after adding to docker group |
| pyenv: command not found | Restart your terminal after editing shell profile |
| GitHub invite not received | Contact your manager — IT needs to resend |

---

## Related Documents

- `vpn_access.md` — VPN setup required before Kubernetes and AWS access
- `day1_checklist.md` — Your Day 1 guide
- `deployment_guide.md` — How to deploy once your environment is set up
