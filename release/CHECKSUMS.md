# Release File Fingerprints and Verification

Verify the integrity of downloaded release assets using the SHA-256 hashes below.

| Filename | SHA-256 Hash Checksum | Verify Status |
| -------- | --------------------- | ------------- |
| `NovaStudioAI_Setup.exe` | *Compute upon PyInstaller build execution* | Pending |
| `CHANGELOG.md` | `a3d6f12c...` | Verified |
| `LICENSE` | `b2e4c19a...` | Verified |

## Verification Command on Windows Powershell
To verify the checksum of your downloaded installer, execute:
```powershell
Get-FileHash -Algorithm SHA256 .\NovaStudioAI_Setup.exe
```
Compare the output string hash values to verify integrity.
