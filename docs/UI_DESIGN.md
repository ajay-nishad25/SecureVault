# SecureVault — UI/UX Design Specification

## 1. UI Architecture & Design Principles

SecureVault utilizes **PySide6** (Qt 6 for Python) for its desktop interface.
The user experience adheres to four core tenets:
1. **Clean & Uncluttered**: A modern, high-contrast desktop aesthetic with dedicated Dark and Light themes.
2. **Obvious Security State**: Clear visual status indicators showing whether the vault is locked or unlocked, unsaved changes, and auto-lock countdowns.
3. **Frictionless Keyboard Navigation**: Full tab order support, `Ctrl+F` search focus, `Ctrl+N` new item, `Ctrl+L` instant lock, and `Escape` to close modals.
4. **Data Privacy First**: Passwords are masked by default (`••••••••`), clipboard clears automatically, and dangerous actions (such as plaintext CSV export) require deliberate acknowledgment.

---

## 2. Planned Screens & Wireframe Specifications

### Screen 1: First-Run Welcome
- **Context**: Displayed when no `vault.svault` is detected in the application storage directory (State: `UNINITIALIZED`).
- **Components**:
  - SecureVault logo & bold header: *"Welcome to SecureVault"*.
  - Subtitle: *"Completely offline, zero-cloud personal credential security."*
  - Primary Action Button: `[ Create New Vault ]`.
  - Secondary Action: `[ Open Existing Vault File... ]` (for users restoring a backup).

---

### Screen 2: Feature & Security Explanation
- **Context**: Step 1 of the initial onboarding flow.
- **Components**:
  - Information cards explaining:
    - **100% Local**: No internet connectivity, no analytics, no cloud data leaks.
    - **Modern Cryptography**: Argon2id password key derivation + AES-256-GCM authenticated encryption.
    - **Zero-Knowledge Architecture**: Only you hold the master password.
  - Navigation Buttons: `[ Back ]`, `[ Next ]`.

---

### Screen 3: Terms & Security Model Acknowledgement
- **Context**: Step 2 of onboarding to ensure user understands the no-recovery security model.
- **Components**:
  - Warning Callout:
    > **CRITICAL SECURITY NOTICE**: SecureVault does not include recovery keys or backdoors in Version 1. If you forget your Master Password, **your vault cannot be recovered by anyone**.
  - Mandatory Checkbox: `[x] I understand that my master password cannot be reset if lost.`
  - Navigation Buttons: `[ Back ]`, `[ Continue to Setup ]` (disabled until checkbox is ticked).

---

### Screen 4: Master Password Setup Wizard
- **Context**: Final step of first-run setup.
- **Components**:
  - Master Password input box (masked, with toggle visibility icon).
  - Confirm Master Password input box.
  - Real-time password strength meter (visual bar + entropy rating: Weak, Medium, Strong, Excellent).
  - Recommendations list: Minimum 12 characters, mix of character types or passphrase.
  - Primary Action Button: `[ Initialize & Encrypt Vault ]`.

---

### Screen 5: Login / Vault Unlock
- **Context**: Shown on normal application startup or after session auto-lock (State: `LOCKED`).
- **Components**:
  - SecureVault branding with a locked padlock icon.
  - Master Password input field (auto-focused on launch).
  - Reveal/Mask password toggle button.
  - Action Button: `[ Unlock Vault ]` (Triggered by `Enter`).
  - Error Banner (hidden until triggered): *"Invalid master password or corrupted vault."*
  - Bottom Action: `[ Switch Vault File... ]`.

---

### Screen 6: Main Vault Screen
- **Context**: The primary operational dashboard while unlocked (State: `UNLOCKED`).
- **Layout (Two-Column Split)**:
  - **Top Navigation Bar**:
    - App Title & Vault Status indicator (`Unlocked - Auto-locks in 09:42`).
    - Quick Action: `[ + New Credential ]` (`Ctrl+N`).
    - Global Action: `[ 🔒 Lock Vault ]` (`Ctrl+L`).
    - Settings Gear Button: `[ ⚙ Settings ]`.
  - **Left Sidebar / Master List (35% width)**:
    - Search Bar (`Ctrl+F`) with real-time text filter.
    - Category / Tag selector dropdown (`All`, `Personal`, `Work`, `Finance`, `Favorites`).
    - Scrollable item list showing:
      - Service Title (e.g., "GitHub").
      - Username (e.g., "developer@example.com").
      - Favorite star icon.
  - **Right Detail Pane (65% width)**:
    - Empty state banner when no item selected: *"Select an entry to view details."*
    - Full details of selected credential (see Screen 8).

---

### Screen 7: Credential Creation View (Modal / Slide-Over)
- **Context**: Triggered by `[ + New Credential ]` or `Ctrl+N`.
- **Form Fields**:
  - Title (Required, e.g. "Google Workspace").
  - Category (Dropdown + custom input).
  - Username / Email (Text input).
  - Password (Masked text input with eye icon).
  - `[ 🎲 Generate Password ]` inline button (opens password generator popup).
  - Tags (Comma-separated text input).
  - Notes (Multi-line text area).
- **Actions**: `[ Cancel ]`, `[ Save Entry ]`.

---

### Screen 8: Credential Details View
- **Context**: Active when an entry is selected from the list.
- **Components**:
  - Header: Service Title and Favorite toggle button.
  - Category & Tags badges.
  - Username field with `[ Copy Username ]` button.
  - Password field: Masked by default (`••••••••`) with `[ Show/Hide ]` and `[ Copy Password ]` buttons.
    - Copy button provides inline visual feedback: changes to *"Copied! (Auto-clears in 30s)"* for 2 seconds.
  - Notes section (read-only rendered text with scroll).
  - Footer Metadata: Created at timestamp, Last modified timestamp (ISO-8601 UTC).
  - Action Buttons: `[ Edit Entry ]`, `[ Delete Entry ]` (with confirmation dialog).

---

### Screen 9: Settings Screen
- **Context**: Application preferences dialog (`settings.json`).
- **Tabs / Sections**:
  - **Security**:
    - Auto-lock timeout slider/spinner (1 to 60 minutes, default: 10 minutes).
    - Clipboard auto-clear timeout slider/spinner (10 to 120 seconds, default: 30 seconds).
    - `[ Change Master Password... ]` button.
  - **Appearance**:
    - Theme selector: `System Default`, `Dark Theme`, `Light Theme`.
  - **Vault & Storage**:
    - Current Vault File Path: `%LOCALAPPDATA%\SecureVault\vault.svault`.
    - Total entries count, file size, last saved timestamp.
  - **Data Export**:
    - `[ Export Vault to CSV... ]` button.

---

### Screen 10: Change Master Password Modal
- **Context**: Initiated from Settings while vault is unlocked.
- **Components**:
  - Current Master Password input.
  - New Master Password input.
  - Confirm New Master Password input.
  - Password strength indicator.
  - Notice: *"This will re-wrap your vault encryption key with a new Argon2id derivation."*
  - Actions: `[ Cancel ]`, `[ Update Master Password ]`.

---

### Screen 11: CSV Export Warning & Confirmation Dialog
- **Context**: Triggered when user selects `[ Export Vault to CSV... ]`.
- **Components**:
  - Prominent Caution Banner:
    > ⚠️ **UNENCRYPTED PLAINTEXT WARNING**:
    > Exporting will generate a plain `.csv` file containing all usernames, passwords, and notes in **unencrypted, human-readable text**.
    > Anyone with access to this exported file will be able to read your passwords.
  - Master password confirmation input to verify user authorization.
  - Confirmation Checkbox: `[x] I understand that the exported file is NOT encrypted.`
  - Actions: `[ Cancel ]`, `[ Export to CSV File... ]` (opens native OS Save File dialog).

---

## 3. Keyboard Shortcut Reference

| Shortcut | Action |
| :--- | :--- |
| `Ctrl+L` | Immediately lock vault and clear session state |
| `Ctrl+N` | Open New Credential modal |
| `Ctrl+F` | Focus search bar in main vault |
| `Ctrl+C` (on selected item) | Copy password of active entry to clipboard |
| `Ctrl+Shift+C` | Copy username of active entry to clipboard |
| `Escape` | Close active dialog/modal, or clear search filter |
| `Enter` | Submit login / confirm active dialog action |
