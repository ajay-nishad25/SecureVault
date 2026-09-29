# SecureVault — Vault Data Format Specification

## 1. File Envelope Design

The primary vault database is stored as a single binary file with the extension `.svault` (default path: `%LOCALAPPDATA%\SecureVault\vault.svault` on Windows).

The format is structured as an explicit binary envelope containing two distinct sections:
1. **The Fixed Header & Wrapped Key Envelope (134 bytes / `0x86`)**: Contains format identification, KDF parameters, cryptographic salt, the KEK-wrapped Data Encryption Key (DEK), and payload metadata (length, nonce, authentication tag).
2. **The Encrypted Payload**: Contains the AES-256-GCM ciphertext of the UTF-8 encoded JSON credential database.

```
+-------------------------------------------------------------------------+
|                       PUBLIC HEADER (38 bytes)                          |
|  - Magic Bytes: 8 bytes ("SVAULT01")                                    |
|  - Format Version: 2 bytes uint16                                       |
|  - KDF Identifier: 1 byte (0x01 = Argon2id)                             |
|  - KDF Memory Cost (m): 4 bytes uint32 (in KiB)                         |
|  - KDF Iterations (t): 4 bytes uint32                                   |
|  - KDF Parallelism (p): 2 bytes uint16                                  |
|  - Salt Length: 1 byte (0x10 = 16 bytes)                                |
|  - Salt: 16 bytes raw CSPRNG                                            |
+-------------------------------------------------------------------------+
|                     WRAPPED KEY ENVELOPE (60 bytes)                     |
|  - DEK Nonce: 12 bytes raw CSPRNG                                       |
|  - Wrapped DEK: 32 bytes AES-256-GCM ciphertext                         |
|  - DEK Auth Tag: 16 bytes GCM tag                                       |
+-------------------------------------------------------------------------+
|                    PAYLOAD METADATA ENVELOPE (36 bytes)                 |
|  - Payload Length: 8 bytes uint64 big-endian                            |
|  - Payload Nonce: 12 bytes raw CSPRNG                                   |
|  - Payload Auth Tag: 16 bytes GCM tag                                   |
+-------------------------------------------------------------------------+
|                     ENCRYPTED PAYLOAD (Variable)                        |
|  - Payload Ciphertext: PAYLOAD_LEN bytes (AES-256-GCM of UTF-8 JSON)    |
+-------------------------------------------------------------------------+
```

---

## 2. Detailed Byte Layout & Offset Verification

The fixed header spans offsets `0x00` through `0x85` inclusive, totaling **exactly 134 bytes (`0x86`)**. The payload ciphertext begins at byte offset 134 (`0x86`).

| Offset (Hex) | Offset (Dec) | Field Name | Data Type | Size (Bytes) | Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `0x00 - 0x07` | `0 - 7` | `MAGIC` | ASCII String | 8 | Fixed magic identifier: `b'SVAULT01'` |
| `0x08 - 0x09` | `8 - 9` | `FORMAT_VERSION`| Big-Endian uint16 | 2 | Format specification version (currently `1`) |
| `0x0A` | `10` | `KDF_ID` | uint8 | 1 | `0x01` = Argon2id |
| `0x0B - 0x0E` | `11 - 14` | `KDF_MEMORY` | Big-Endian uint32 | 4 | Memory cost in KiB (default: `65536` for 64 MiB) |
| `0x0F - 0x12` | `15 - 18` | `KDF_TIME` | Big-Endian uint32 | 4 | Iteration / time cost (default: `3`) |
| `0x13 - 0x14` | `19 - 20` | `KDF_PARALLEL` | Big-Endian uint16 | 2 | Parallelism lanes (default: `4`) |
| `0x15` | `21` | `SALT_LEN` | uint8 | 1 | Salt length in bytes (`16`) |
| `0x16 - 0x25` | `22 - 37` | `SALT` | Binary bytes | 16 | Random 128-bit CSPRNG salt |
| `0x26 - 0x31` | `38 - 49` | `DEK_NONCE` | Binary bytes | 12 | 96-bit AES-GCM nonce for DEK encryption |
| `0x32 - 0x51` | `50 - 81` | `WRAPPED_DEK` | Binary bytes | 32 | AES-256-GCM ciphertext of 32-byte DEK |
| `0x52 - 0x61` | `82 - 97` | `DEK_TAG` | Binary bytes | 16 | 128-bit GCM authentication tag for wrapped DEK |
| `0x62 - 0x69` | `98 - 105`| `PAYLOAD_LEN` | Big-Endian uint64 | 8 | Length in bytes of `PAYLOAD_CIPHER` |
| `0x6A - 0x75` | `106 - 117`| `PAYLOAD_NONCE`| Binary bytes | 12 | 96-bit AES-GCM nonce for vault payload |
| `0x76 - 0x85` | `118 - 133`| `PAYLOAD_TAG` | Binary bytes | 16 | 128-bit GCM authentication tag for payload |
| `0x86 - END` | `134 - ...` | `PAYLOAD_CIPHER`| Binary bytes | Variable | AES-256-GCM ciphertext of the JSON string |

- **Subtotals Verification**:
  - Public Header (`0x00 - 0x25`): $8 + 2 + 1 + 4 + 4 + 2 + 1 + 16 = 38\text{ bytes}$
  - Wrapped Key Envelope (`0x26 - 0x61`): $12 + 32 + 16 = 60\text{ bytes}$
  - Payload Metadata (`0x62 - 0x85`): $8 + 12 + 16 = 36\text{ bytes}$
  - **Total Static Header Size**: $38 + 60 + 36 = 134\text{ bytes}\ (0x86)$
  - First byte of payload ciphertext: offset $134\ (0x86)$

---

## 3. Associated Authenticated Data (AAD) Specification

To protect against header manipulation, parameter tampering, and truncation, AES-256-GCM binds unencrypted metadata via Additional Authenticated Data (AAD). Encryption and decryption **must** use identical byte-level AAD definitions.

### 3.1 AAD for Wrapped DEK (`AAD_DEK`)
When wrapping (encrypting) or unwrapping (decrypting) the Data Encryption Key with the password-derived KEK:
- **Definition**: The entire 38-byte Public Header from offset `0x00` to `0x25` inclusive.
  $$\text{AAD\_DEK} = \text{file\_bytes}[0\text{x}00 : 0\text{x}26]$$
- **Fields Bound**: `MAGIC` (8B) + `FORMAT_VERSION` (2B) + `KDF_ID` (1B) + `KDF_MEMORY` (4B) + `KDF_TIME` (4B) + `KDF_PARALLEL` (2B) + `SALT_LEN` (1B) + `SALT` (16B).
- **Security Guarantees**:
  - Prevents downgrade of KDF parameters (memory cost, iterations, parallelism).
  - Binds the salt directly to the derived key wrap.
  - Ensures any unauthorized modification of the public header causes DEK decryption to immediately fail tag verification.

### 3.2 AAD for Encrypted Payload (`AAD_PAYLOAD`)
When encrypting or decrypting the vault payload JSON with the DEK:
- **Definition**: The 10-byte file identifier/version prefix concatenated with the 8-byte payload length field.
  $$\text{AAD\_PAYLOAD} = \text{file\_bytes}[0\text{x}00 : 0\text{x}0A] \parallel \text{file\_bytes}[0\text{x}62 : 0\text{x}6A]$$
- **Total AAD Length**: Exactly 18 bytes.
- **Fields Bound**: `MAGIC` (8B) + `FORMAT_VERSION` (2B) + `PAYLOAD_LEN` (8B).
- **Architectural Rationale**:
  - **Master Password Independence**: `AAD_PAYLOAD` deliberately **excludes** the salt, KDF parameters, and wrapped DEK fields (`0x0B - 0x61`). Consequently, when the user changes their master password, a new salt and new wrapped DEK are written to the file header, but **the payload ciphertext and its authentication tag remain 100% valid without requiring re-encryption of the payload**.
  - **Truncation Protection**: Authenticating `PAYLOAD_LEN` ensures that any trailing truncation, extension, or modification of the length field causes payload decryption to fail tag validation.
  - **Version Binding**: Prevents format version confusion across future upgrades.

---

## 4. Decrypted Payload Schema (JSON)

When decrypted with the DEK, the payload byte sequence represents a UTF-8 encoded JSON document conforming to the following structure:

```json
{
  "schema_version": 1,
  "vault_id": "a9d7b438-c84a-436f-b251-1798dfb01859",
  "created_at": "2026-09-29T14:30:00Z",
  "updated_at": "2026-09-29T14:35:12Z",
  "items": [
    {
      "id": "e301d25b-80df-4f44-93eb-6ea278f237f8",
      "title": "GitHub",
      "username": "developer@example.com",
      "password": "CorrectHorseBatteryStaple#2026",
      "category": "Work",
      "tags": ["code", "git"],
      "notes": "Personal access token stored in notes if needed.",
      "favorite": true,
      "created_at": "2026-09-29T14:31:00Z",
      "updated_at": "2026-09-29T14:34:00Z"
    }
  ]
}
```

### Field Definitions:
- `schema_version` (integer): Internal schema increment counter.
- `vault_id` (string): Canonical UUID4 uniquely identifying the vault.
- `created_at` / `updated_at` (string): ISO-8601 UTC timestamps (`YYYY-MM-DDTHH:MM:SSZ`).
- `items` (array of objects):
  - `id` (string): Unique UUID4 string per entry.
  - `title` (string): Service or account title.
  - `username` (string): Username, handle, or email address.
  - `password` (string): Recoverable credential text.
  - `category` (string): Primary grouping (e.g., "Personal", "Work", "Finance").
  - `tags` (array of strings): Searchable classification tags.
  - `notes` (string): Free-form multi-line text notes.
  - `favorite` (boolean): Flag for starred/pinned entries.
  - `created_at` / `updated_at` (string): ISO-8601 UTC timestamps.

---

## 5. Atomic Storage & Integrity Protection

To prevent data loss or partial writes during unexpected crashes, OS terminates, or power failures:

1. **Write to Temporary File**: The updated payload is serialized, encrypted with a fresh random nonce, and written along with the complete 134-byte header to `%LOCALAPPDATA%\SecureVault\vault.svault.tmp`.
2. **Buffer Flush and OS Sync**:
   ```python
   file.flush()
   os.fsync(file.fileno())
   ```
3. **Atomic Replacement**:
   ```python
   os.replace(tmp_path, target_path)
   ```
   `os.replace` atomically updates the file pointer on modern file systems (NTFS on Windows, ext4 on Linux). In the event of an abrupt interruption, the previous valid `vault.svault` remains uncorrupted.
