# SecureVault — UI/UX Design Specification

## 1. UI Architecture & Design Principles

SecureVault utilizes **PySide6** (Qt 6 for Python) for its desktop interface.
The user experience adheres to four core tenets:
1. **Clean & Uncluttered**: A modern, high-contrast desktop aesthetic with dedicated Dark and Light themes.
2. **Obvious Security State**: Clear visual status indicators showing whether the vault is `UNINITIALIZED`, `LOCKED`, or `UNLOCKED`.
3. **Frictionless Keyboard Navigation**: Full tab order support, `Ctrl+F` search focus, `Ctrl+N` new item, `Ctrl+L` instant lock, and `Escape` to close modals.
4. **Data Privacy First**: Passwords are masked by default (`••••••••`), clipboard clears automatically, and secrets are handled strictly in-memory.

---

## 2. Planned Screens & Implementation Specifications

### Screen 1: First-Run Setup Wizard (`app.ui.setup.wizard.SetupWizard`)
- **Context**: Displayed when the application is in the `UNINITIALIZED` state (no initialization marker found).
- **Architecture**: Implemented as a 7-step PySide6 `QWizard` (`QWizard.WizardStyle.ModernStyle`).
- **Steps**:
  1. **WelcomePage**:
     - Introduces SecureVault as a completely offline, local-first personal password manager.
     - Outlines key principles: 100% offline, local custody, open & auditable.
  2. **FeaturesPage**:
     - Explains offline-first architecture, local encrypted vault, user-controlled master password, and zero cloud sync in v1.
  3. **AcknowledgementPage**:
     - Prominent critical security notice: No password recovery mechanism in Version 1.
     - Mandatory checkbox: `[ ] I understand that SecureVault v1 has no password recovery mechanism.`
     - Next button is strictly disabled until the checkbox is checked.
  4. **LoginIdPage**:
     - Input field for non-secret `Login ID` (e.g. username or email).
     - Validation: 3–64 characters, alphanumeric plus `.`, `_`, `-`, and `@`.
     - Rejects reserved system names (`admin`, `root`, `superuser`, `null`).
     - Real-time feedback indicator (green checkmark or red error message).
     - Next button is disabled until valid input is provided.
  5. **MasterPasswordPage**:
     - `Master Password` input box (masked by default).
     - `Confirm Password` input box (masked by default).
     - "Show password" toggle checkbox.
     - Advisory local password strength meter (score 0–100, ratings: Empty, Weak, Medium, Strong, Very Strong).
     - Validation: minimum 8 characters, both fields must match identically.
     - Next button is disabled until passwords match and satisfy length requirements.
  6. **FinalWarningPage**:
     - Displays summary: configured Login ID, password status (`[Configured]`), and recovery status (`None`).
     - Mandatory confirmation checkbox: `[ ] I understand and want to initialize SecureVault.`
     - Finish/Next button is disabled until confirmed.
  7. **CompletionPage**:
     - Informs the user that setup is complete and explains the transition to the `LOCKED` state.
     - Clicking "Finish" initializes the non-sensitive state and transitions to `LockedView`.
- **Cancellation**:
  - Clicking "Cancel" on any wizard page leaves the application completely uninitialized and clears all in-memory password inputs.

---

### Screen 2: Locked View / Future Login Placeholder (`app.ui.locked_view.LockedView`)
- **Context**: Displayed when the application is in the `LOCKED` state.
- **Components**:
  - Padlock icon and header: *"SecureVault — Locked"*.
  - User profile display: shows configured `Login ID`.
  - Informational notice: *"State: LOCKED. Master password authentication will be enabled in Milestone 3 (M3)."*
  - Buttons:
    - `[ Exit Application ]`: Closes the application.
    - `[ Reset Setup (Dev) ]`: Clears the initialization marker to facilitate re-testing of the first-run wizard.

---

### Screen 3: Login / Vault Unlock (Milestone M3)
- **Context**: Displayed upon application launch when initialized.
- **Components**:
  - SecureVault branding with a locked padlock icon.
  - Master Password input field (auto-focused on launch).
  - Reveal/Mask password toggle button.
  - Action Button: `[ Unlock Vault ]` (Triggered by `Enter`).
  - Error Banner (hidden until triggered): *"Invalid master password or corrupted vault."*
  - Bottom Action: `[ Switch Vault File... ]`.

---

### Screen 3b: Unlocked Vault & Credential Management (Milestone M5)
- **Context**: Displayed upon successful cryptographic unlock in Milestone M5 (`UNLOCKED` state).
- **Components**:
  - Header with profile ID, vault ID, and stored credential count.
  - Scrollable credential list rendering `CredentialCardWidget` entries:
    - Title, username, and notes preview.
    - Dedicated per-entry buttons: `[ 👁 View ]`, `[ ✏️ Edit ]`, `[ 🗑 Delete ]`.
  - Global Actions: `[ ➕ Add Credential ]`, `[ 🔒 Lock Vault ]`, `[ Exit ]`.
  - Smooth pixel-based scrolling (`ScrollPerPixel`) with fluid mouse-wheel navigation.
  - **Delete Confirmation Modal**:
    - Triggered by clicking `[ 🗑 Delete ]` on any card.
    - Prompts with: *"Are you sure you want to delete '{title}'? This action cannot be undone."*
    - Actions: `[ Cancel ]` (aborts deletion), `[ Delete ]` (permanently deletes entry and persists changes).
  - **View Credential Modal (`ViewCredentialDialog`)**:
    - Read-only display of Title, Username, Password, and Notes.
    - Password is masked by default with `[ Show ]` / `[ Hide ]` toggle button.
    - No "type" field. Read-only without modifying credential or vault.
  - **Edit Credential Modal (`EditCredentialDialog`)**:
    - Editable form pre-populated with existing Title, Username, Password, and Notes.
    - Password is masked by default with `[ Show ]` / `[ Hide ]` toggle.
    - Untouched password is preserved without overwrite.
    - Input validation rejects empty required fields and keeps dialog open with error.
    - Saves changes via `CredentialService.update_credential()` and atomic re-encryption.
  - **Add Credential Modal (`AddCredentialDialog`)**:
    - Creation form with field validation and masked password input.

---

### Screen 4: Main Vault Screen (Milestone M6)
- **Context**: The primary operational dashboard while unlocked (`UNLOCKED` state).
- **Layout (Two-Column Split)**:
  - **Top Navigation Bar**:
    - App Title & Vault Status indicator (`Unlocked - Auto-locks in 09:42`).
    - Quick Action: `[ + New Credential ]` (`Ctrl+N`).
    - Global Action: `[ 🔒 Lock Vault ]` (`Ctrl+L`).
    - Settings Gear Button: `[ ⚙ Settings ]`.
  - **Left Sidebar / Master List (35% width)**:
    - Search Bar (`Ctrl+F`) with real-time text filter.
    - Category / Tag selector dropdown (`All`, `Personal`, `Work`, `Finance`, `Favorites`).
    - Scrollable item list showing title, username, and favorite star icon.
  - **Right Detail Pane (65% width)**:
    - Details of selected credential, masked password with copy and reveal buttons.

---

### Screen 5: Credential Creation Modal (Milestone M6)
- **Context**: Triggered by `[ + New Credential ]` or `Ctrl+N`.
- **Form Fields**: Title, Category, Username, Password (with generate button), Tags, Notes.
- **Actions**: `[ Cancel ]`, `[ Save Entry ]`.

---

### Screen 6: Credential Details View (Milestone M6)
- **Context**: Active when an entry is selected from the list.
- **Components**: Service Title, category/tags badges, username with copy button, masked password with show/hide and copy buttons (with 30s auto-clear feedback), notes area, timestamps, and edit/delete actions.

---

### Screen 7: Settings Screen (Milestone M8)
- **Context**: Application preferences dialog (`settings.json`).
- **Tabs**: Security (auto-lock timer, clipboard timer, change password), Appearance (theme selection), Storage location.

---

### Screen 8: Change Master Password Modal (Milestone M9)
- **Context**: Re-wraps the DEK with a new master password and fresh salt.

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
