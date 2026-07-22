# Code Signing Setup

SessionGuard supports code signing for all desktop platforms.

## Windows

### Development (Self-signed)

For local testing, create a self-signed certificate:

```powershell
New-SelfSignedCertificate -Type CodeSigningCert -Subject "CN=SessionGuard Dev" -CertStoreLocation Cert:\CurrentUser\My
```

Export and import:

```powershell
$cert = Get-ChildItem -Path Cert:\CurrentUser\My | Where-Object { $_.Subject -eq "CN=SessionGuard Dev" }
Export-PfxCertificate -Cert $cert -FilePath "sessionguard.pfx" -Password (ConvertTo-SecureString -String "password" -Force -AsPlainText)
```

For testing, Tauri can use the PFX with the `TAURI_SIGNING_WINDOWS_CERTIFICATE` env var.

### Production

1. Purchase a code signing certificate (standard OV cert, ~$50-100/year)
2. Set in `tauri.conf.json` bundle.signing.windows.identity:
   - Certificate name: `SessionGuard Code Signing`
   - Or certificate thumbprint: `xy:zw:...`

For CI/CD, use GitHub Actions secrets:
- `WINDOWS_CERTIFICATE` — Base64-encoded PFX
- `WINDOWS_CERTIFICATE_PASSWORD` — PFX password

```yaml
- name: Build Tauri app (windows)
  env:
    WINDOWS_CERTIFICATE: ${{ secrets.WINDOWS_CERTIFICATE }}
    WINDOWS_CERTIFICATE_PASSWORD: ${{ secrets.WINDOWS_CERTIFICATE_PASSWORD }}
  run: |
    echo "$WINDOWS_CERTIFICATE" | base64 -d > certificate.pfx
    cargo tauri build
```

## macOS

### Development (Ad-hoc)

Ad-hoc signing works for local testing. Set `identity: "-"` in tauri.conf.json.

### Production (Apple Developer)

1. Join Apple Developer Program ($99/year)
2. Create a signing certificate in Xcode or App Store Connect
3. Export to your keychain: `security import "Certificates.p12" -k ~/Library/Keychains/login.keychain`
4. Set `tauri.conf.json` bundle.signing.macOS.identity to your certificate name

For CI/CD, use GitHub Actions:

```yaml
- name: macOS build
  env:
    APPLE_SIGNING_IDENTITY: ${{ secrets.APPLE_SIGNING_IDENTITY }}
    APPLE_CERTIFICATE: ${{ secrets.APPLE_CERTIFICATE }}
    APPLE_CERTIFICATE_PASSWORD: ${{ secrets.APPLE_CERTIFICATE_PASSWORD }}
    KEYCHAIN_PASSWORD: ${{ secrets.KEYCHAIN_PASSWORD }}
  run: |
    # Create证书
    CERT_DIR=$RUNNER_TEMP/certs
    mkdir -p $CERT_DIR
    echo -n "$APPLE_CERTIFICATE" | base64 -D -o $CERT_DIR/certificate.p12
    
    # Import to keychain
    security create-keychain -p "$KEYCHAIN_PASSWORD" $RUNNER_TEMP/app-signing.keychain-db
    security set-keychain-password -p "$KEYCHAIN_PASSWORD" $RUNNER_TEMP/app-signing.keychain-db
    security import $CERT_DIR/certificate.p12 -P "$APPLE_CERTIFICATE_PASSWORD" -A -t cert -f pkcs12 -k $RUNNER_TEMP/app-signing.keychain-db
    security list-keychain -d user -s $RUNNER_TEMP/app-signing.keychain-db
    
    cargo tauri build
```

## Environment Variables

| Variable | Platform | Purpose |
|----------|----------|---------|
| `TAURI_SIGNING_WINDOWS_IDENTITY` | Windows | Certificate name or thumbprint |
| `TAURI_SIGNING_MACOS_IDENTITY` | macOS | Certificate name |
| `APPLE_SIGNING_IDENTITY` | macOS | Full certificate identity for notarization |

## Notarization (macOS)

For distribution outside the App Store, notarization is required. After signing, run:

```bash
xcrun notarytool submit SessionGuard.app --apple-id "your@email.com" --password "app-password" --team-id "TEAMID"
xcrun stapler staple SessionGuard.app
```

See `.github/workflows/build.yml` for automated notarization.