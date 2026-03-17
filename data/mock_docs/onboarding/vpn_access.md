# VPN & Remote Access Guide

**Last Updated:** January 2025
**Owner:** IT Security
**Tags:** onboarding, vpn, remote-access, security, mfa

---

## Overview

All access to internal TechCorp systems — Kubernetes clusters, bastion hosts, internal APIs, and data platforms — requires an active VPN connection. This page covers VPN setup, MFA configuration, and SSH key management.

---

## Step 1: Multi-Factor Authentication (MFA)

MFA must be set up before the VPN client will work.

1. Download the **Okta Verify** app on your mobile phone (iOS or Android)
2. Navigate to `https://techcorp.okta.com` on your laptop
3. Log in with your corporate credentials
4. When prompted, scan the QR code using Okta Verify
5. Enter the 6-digit code from the app to confirm setup
6. Save your backup codes in a secure location — you will need them if you lose your phone

> **Important:** Do not use SMS as your MFA method. Okta Verify or a hardware key (YubiKey) are the only approved methods.

---

## Step 2: VPN Client Installation

TechCorp uses **GlobalProtect** as the VPN client.

### macOS
1. Download the installer from `https://vpn.techcorp.com/global-protect/msi-64`
2. Open the `.pkg` file and follow the installation wizard
3. Open GlobalProtect from your Applications folder
4. Enter the portal address: `vpn.techcorp.com`
5. Log in with your corporate credentials
6. Approve the MFA prompt in Okta Verify

### Ubuntu
```bash
# Download the .deb package from the IT portal
sudo dpkg -i GlobalProtect_UI_deb-6.x.x.deb

# Start the service
sudo systemctl start gpd
globalprotect connect --portal vpn.techcorp.com
```

---

## Step 3: Verify VPN Connection

Once connected, verify internal network access:
```bash
# Ping the internal DNS resolver
ping internal.techcorp.net

# Confirm you can reach the Kubernetes API
kubectl get nodes

# Check access to the bastion host (once Unix access is provisioned)
ssh bastion.techcorp.internal
```

---

## Step 4: SSH Key Setup

SSH access to servers uses key-based authentication only. Password authentication is disabled.

### Generate Your SSH Key
```bash
ssh-keygen -t ed25519 -C "your.name@techcorp.com" -f ~/.ssh/techcorp_ed25519
```

When prompted for a passphrase, **set a strong passphrase** — do not leave it empty.

### Add Key to SSH Agent
```bash
# Start the agent
eval "$(ssh-agent -s)"

# Add your key
ssh-add ~/.ssh/techcorp_ed25519
```

### Register Your Public Key
1. Copy your public key:
```bash
cat ~/.ssh/techcorp_ed25519.pub
```
2. Submit the key via ServiceNow using ticket type `SSH_KEY_REGISTRATION`
3. IT will add your key to the bastion host within 24 hours
4. You will receive a confirmation email when access is provisioned

### SSH Config
Add this to your `~/.ssh/config` to simplify connections:
```
Host bastion
    HostName bastion.techcorp.internal
    User your.username
    IdentityFile ~/.ssh/techcorp_ed25519
    ServerAliveInterval 60

Host *.techcorp.internal
    ProxyJump bastion
    User your.username
    IdentityFile ~/.ssh/techcorp_ed25519
```

---

## Access Levels

| Environment | VPN Required | SSH Access Required | Who Has Access |
|---|---|---|---|
| Development | Yes | No | All engineers |
| Staging | Yes | Yes | All engineers after Day 30 |
| Production | Yes | Yes + approval | Senior engineers only |

Production SSH access requires a separate access request after your first 30 days.

---

## VPN Troubleshooting

| Issue | Fix |
|---|---|
| VPN connects but can't reach internal services | Check your DNS settings — set primary DNS to `10.0.0.1` |
| MFA prompt not appearing | Ensure Okta Verify app is not in battery saver mode |
| GlobalProtect says "Portal unreachable" | Check your internet connection, then retry |
| SSH: Permission denied (publickey) | Your key is not registered yet — raise a ServiceNow ticket |
| SSH: Connection timed out | Ensure VPN is connected before attempting SSH |
| Disconnected after 1 hour of inactivity | Expected behaviour — reconnect via GlobalProtect |

---

## Security Policies

- Never leave your VPN connected on public Wi-Fi without additional endpoint protection
- Do not share VPN credentials
- If your laptop is lost or stolen, report immediately to `security@techcorp.com` — your VPN access will be revoked
- VPN session logs are retained for 90 days for security audit purposes

---

## Related Documents

- `tools_setup.md` — Full developer environment setup
- `day1_checklist.md` — First day guide
