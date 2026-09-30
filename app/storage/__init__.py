"""SecureVault Storage Subsystem.

Architectural Boundary:
This package encapsulates file persistence:
  - Reading and writing the 134-byte fixed header binary envelope (.svault)
  - Atomic file write semantics (write-to-temp-then-rename via os.replace)
  - Non-sensitive settings JSON persistence (settings.json)

Note: Storage engine implementation is scheduled for Milestone M4.
"""
