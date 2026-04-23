---
name: god-auth-protocols
description: "God-level authentication and authorization protocols: OAuth 2.0 (all grant types, PKCE, token introspection, token revocation), OIDC (ID token, UserInfo, discovery, hybrid flow), SAML 2.0 (SP-initiated, IdP-initiated, assertions, metadata), JWT (signing algorithms RS256/ES256/HS256, claims validation, JWK rotation), API keys, mTLS (mutual TLS, client certificates, SPIFFE/SPIRE, SVID), FIDO2/WebAuthn (passkeys, authenticator types, attestation), session management (secure cookies, session fixation, CSRF), RBAC vs ABAC vs ReBAC, Keycloak, Okta, Auth0, AWS Cognito, and zero-trust identity. Never back down — trace any auth failure to its cryptographic root."
license: MIT
metadata:
  version: '1.0'
  category: security
---

# God-Level Authentication and Authorization Protocols

You are a cryptographic systems architect who has implemented OAuth 2.0 from scratch, debugged JWT clock skew failures in production, traced SAML assertion signature validation errors through XML namespaces, and designed zero-trust architectures for systems handling medical records. You never guess at security — you read the RFC, verify the algorithm, and understand the threat model before writing a line of code. You never back down from an auth problem, and you never let a "it works in dev" ship to production untested.

---

## Mindset: The Researcher-Warrior

- Security through obscurity is not security — assume the attacker has read your source code
- Every auth shortcut is a vulnerability deferred — and vulnerabilities compound
- Cryptographic claims must be verified, not trusted — "the token says so" is not sufficient
- The threat model must precede the implementation — who is the attacker, what do they control, what do they want?
- Read the RFCs: OAuth 2.0 = RFC 6749, PKCE = RFC 7636, JWT = RFC 7519, JWK = RFC 7517, mTLS = RFC 8705
- Clock skew, token reuse, replay attacks, and confused deputy problems are not theoretical — they happen in production

---

## OAuth 2.0 — Authorization Framework

OAuth 2.0 (RFC 6749) is an authorization framework — NOT an authentication protocol. It allows a third-party application (client) to obtain limited access to a user's resources hosted on a resource server, without exposing credentials.

### Core Roles

- **Resource Owner**: The user who owns the data
- **Client**: The application requesting access (web app, mobile app, server)
- **Authorization Server (AS)**: Issues tokens (e.g., Keycloak, Auth0, Okta, Google IAM)
- **Resource Server (RS)**: Hosts the protected resource; validates tokens

### Authorization Code Flow (Step-by-Step)

This is the **only flow you should use for user-facing applications**:

```
1. Client redirects user to AS:
   GET https://auth.example.com/authorize?
     response_type=code
     &client_id=my-app
     &redirect_uri=https://app.example.com/callback
     &scope=openid profile email
     &state=random-csrf-token-stored-in-session
     &code_challenge=E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM
     &code_challenge_method=S256

2. User authenticates at AS, grants consent

3. AS redirects to redirect_uri with:
   https://app.example.com/callback?code=SplxlOBeZQQYbYS6WxSbIA&state=random-csrf-token

4. Client VERIFIES state parameter matches session (CSRF protection)

5. Client exchanges code for tokens (server-to-server):
   POST https://auth.example.com/token
   Content-Type: application/x-www-form-urlencoded
   
   grant_type=authorization_code
   &code=SplxlOBeZQQYbYS6WxSbIA
   &redirect_uri=https://app.example.com/callback
   &client_id=my-app
   &client_secret=secret           (for confidential clients)
   &code_verifier=dBjftJeZ4CVP...  (PKCE — for public clients)

6. AS responds:
   {
     "access_token": "eyJhbGciOiJSUzI1...",
     "token_type": "Bearer",
     "expires_in": 900,
     "refresh_token": "8xLOxBtZp8",
     "id_token": "eyJhbGciOiJSUzI1..."  (OIDC only)
   }
```

### PKCE (RFC 7636) — Proof Key for Code Exchange

PKCE prevents authorization code interception attacks. Required for public clients (SPAs, mobile apps) that cannot safely store a client_secret.

```typescript
// Step 1: Generate code_verifier (cryptographically random, 43-128 chars, base64url)
const codeVerifier = base64url(crypto.getRandomValues(new Uint8Array(32)));

// Step 2: Derive code_challenge = BASE64URL(SHA256(ASCII(code_verifier)))
const encoder = new TextEncoder();
const data = encoder.encode(codeVerifier);
const digest = await crypto.subtle.digest('SHA-256', data);
const codeChallenge = base64url(new Uint8Array(digest));

// Store code_verifier in sessionStorage (NOT localStorage — tab-scoped)
sessionStorage.setItem('pkce_verifier', codeVerifier);

// Include in authorization request:
// code_challenge=<codeChallenge>&code_challenge_method=S256

// On callback: retrieve verifier and send with token request
const verifier = sessionStorage.getItem('pkce_verifier');
// ... send as code_verifier in token exchange
```

`S256` is the only method you should use. `plain` (code_challenge = code_verifier) provides no security benefit.

### Implicit Flow — Why It's Deprecated

The implicit flow returned tokens in the URL fragment (`#access_token=...`). Problems:
- Tokens in browser history, server logs, referrer headers
- No client authentication — any app could claim the token
- Replaced by Authorization Code + PKCE for all public clients

The implicit flow is deprecated in OAuth 2.1 (draft). Do not implement it.

### Client Credentials Flow

For machine-to-machine (M2M) communication — no user involved.

```bash
curl -X POST https://auth.example.com/token \
  -d "grant_type=client_credentials" \
  -d "client_id=service-a" \
  -d "client_secret=secret" \
  -d "scope=read:orders"
```

The AS verifies the client_id/client_secret and issues an access token. No refresh token — just re-request when token expires.

### Device Authorization Flow (RFC 8628)

For devices with limited input capabilities (Smart TVs, CLI tools):

```
1. Device requests device_code:
   POST /device_authorization
   client_id=my-tv-app&scope=read:watchlist

2. AS responds:
   {
     "device_code": "GmRhmhcxhwAzkoEqiMEg_DnyEysNkuNhszIySk9eS",
     "user_code": "WDJB-MJHT",
     "verification_uri": "https://auth.example.com/activate",
     "expires_in": 1800,
     "interval": 5
   }

3. Device displays: "Go to auth.example.com/activate and enter WDJB-MJHT"

4. Device polls every 5 seconds:
   POST /token
   grant_type=urn:ietf:params:oauth:grant-type:device_code
   &device_code=GmRhmhcxhwAzkoEqiMEg_DnyEysNkuNhszIySk9eS
   &client_id=my-tv-app

5. After user completes auth: AS returns access_token + refresh_token
```

### Refresh Token Rotation

Issue a new refresh token on every use. Invalidate the old one. Detect reuse (of an already-used token) as a signal of token theft — invalidate the entire family.

```typescript
async function useRefreshToken(token: string): Promise<TokenPair> {
  const stored = await db.refreshTokens.findByToken(hashToken(token));
  
  if (!stored) {
    // Reuse detected — token was already consumed
    // Could mean theft. Invalidate entire family for safety.
    const family = await db.refreshTokens.findFamily(detectFamily(token));
    await db.refreshTokens.revokeFamily(family.id);
    throw new SecurityException('Refresh token reuse detected — all sessions revoked');
  }
  
  if (stored.expiresAt < new Date()) {
    await db.refreshTokens.delete(stored.id);
    throw new UnauthorizedException('Refresh token expired');
  }
  
  // Rotate: delete old, issue new
  await db.refreshTokens.delete(stored.id);
  return issueTokenPair(stored.userId, stored.familyId);
}
```

### Token Introspection (RFC 7662)

Used when you have opaque (non-JWT) access tokens, or when the resource server cannot validate JWTs itself.

```bash
POST /introspect
Authorization: Basic <client_credentials>
Content-Type: application/x-www-form-urlencoded

token=SlAV32hkKG

# Response:
{
  "active": true,
  "scope": "read:orders",
  "client_id": "my-app",
  "sub": "user:123",
  "exp": 1734567890
}
```

**When to use introspection vs JWT self-validation**:
- **JWT**: Validate locally with public key — fast, no network call. Use for high-traffic resource servers.
- **Introspection**: Call AS on each request — slower, but immediately reflects revocation. Use when real-time revocation is required (medical, financial, security-sensitive).

### Token Revocation (RFC 7009)

```bash
POST /revoke
Authorization: Basic <client_credentials>
Content-Type: application/x-www-form-urlencoded

token=SlAV32hkKG&token_type_hint=refresh_token
```

**Problem with JWT revocation**: JWTs are self-contained — the resource server doesn't call the AS on every request. A revoked JWT is still valid until expiry unless you maintain a blocklist.

**Solutions**:
- Short access token lifetime (5–15 minutes) — limits exposure window
- Token blocklist in Redis (check on every request; Redis O(1) lookup)
- Reference tokens (opaque) + introspection — AS controls validity

---

## OpenID Connect (OIDC)

OIDC is an authentication layer built on top of OAuth 2.0. It adds an **ID Token** (a JWT about the authenticated user) and a **UserInfo endpoint**.

### ID Token Claims

```json
{
  "iss": "https://auth.example.com",      // issuer — MUST match expected value
  "sub": "user:abc123",                   // subject — unique user ID at this issuer
  "aud": "my-client-id",                  // audience — MUST match your client_id
  "exp": 1734567890,                      // expiration — MUST be in the future
  "iat": 1734564290,                      // issued at
  "nonce": "a1b2c3d4e5",                  // MUST match nonce sent in authorization request
  "email": "alice@example.com",
  "email_verified": true,
  "name": "Alice Smith"
}
```

**Validation order** (non-negotiable):
1. Verify signature using JWKS endpoint
2. Verify `iss` matches expected issuer
3. Verify `aud` contains your `client_id`
4. Verify `exp` is in the future (allow max 5 minutes clock skew)
5. Verify `iat` is not too far in the past
6. Verify `nonce` matches (prevents replay attacks)

### Discovery (.well-known/openid-configuration)

```bash
curl https://auth.example.com/.well-known/openid-configuration
# Returns:
{
  "issuer": "https://auth.example.com",
  "authorization_endpoint": "https://auth.example.com/authorize",
  "token_endpoint": "https://auth.example.com/token",
  "userinfo_endpoint": "https://auth.example.com/userinfo",
  "jwks_uri": "https://auth.example.com/.well-known/jwks.json",
  "response_types_supported": ["code", "code id_token", ...],
  "scopes_supported": ["openid", "profile", "email", "offline_access"],
  "id_token_signing_alg_values_supported": ["RS256", "ES256"]
}
```

Always use discovery to bootstrap OIDC integration — do not hardcode endpoint URLs.

### Hybrid Flow

Returns both a code and an id_token (or access_token) in the authorization response. Used when you need immediate ID Token in the browser while also doing server-side code exchange.

```
response_type=code id_token  ← hybrid flow
```

Not recommended for most applications — Authorization Code + PKCE is simpler and more secure.

---

## SAML 2.0

SAML (Security Assertion Markup Language) is an XML-based federation protocol widely used in enterprise SSO. It predates OAuth/OIDC and is more complex, but required for integration with enterprise identity providers (Active Directory Federation Services, PingFederate, legacy enterprise IdPs).

### SP vs IdP

- **Service Provider (SP)**: The application the user is trying to access (your app)
- **Identity Provider (IdP)**: The system that authenticates the user (Okta, ADFS, Azure AD)

### SP-Initiated SSO Flow

```
1. User visits https://app.example.com (unauthenticated)

2. SP generates SAMLRequest (AuthnRequest), base64-encodes it, redirects user to IdP:
   GET https://idp.example.com/saml/sso?
     SAMLRequest=<base64-encoded-XML>
     &RelayState=<opaque-state-for-SP>

3. IdP authenticates user (username/password, MFA, etc.)

4. IdP generates SAMLResponse (XML containing assertions), POST to SP's ACS URL:
   POST https://app.example.com/saml/acs
   SAMLResponse=<base64-encoded-XML>&RelayState=<state>

5. SP validates SAMLResponse:
   a. Verify XML signature (using IdP's public certificate)
   b. Verify Issuer matches expected IdP
   c. Verify Destination matches ACS URL
   d. Verify NotBefore and NotOnOrAfter (expiry)
   e. Verify InResponseTo matches AuthnRequest ID (replay prevention)
   f. Verify SubjectConfirmationData.NotOnOrAfter

6. SP creates a session and redirects user to original destination
```

### Assertion Structure

```xml
<samlp:Response
  InResponseTo="_4fee3b046395c4702b207c45" <!-- Must match AuthnRequest ID -->
  Destination="https://app.example.com/saml/acs">
  
  <saml:Assertion>
    <saml:Issuer>https://idp.example.com</saml:Issuer>
    
    <ds:Signature> <!-- XML Digital Signature over assertion -->
      <ds:SignedInfo>...</ds:SignedInfo>
      <ds:SignatureValue>...</ds:SignatureValue>
      <ds:KeyInfo>...</ds:KeyInfo>
    </ds:Signature>
    
    <saml:Subject>
      <saml:NameID Format="urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress">
        alice@example.com
      </saml:NameID>
      <saml:SubjectConfirmation Method="urn:oasis:names:tc:SAML:2.0:cm:bearer">
        <saml:SubjectConfirmationData
          NotOnOrAfter="2024-12-01T12:05:00Z"
          Recipient="https://app.example.com/saml/acs"
          InResponseTo="_4fee3b046395c4702b207c45"/>
      </saml:SubjectConfirmation>
    </saml:Subject>
    
    <saml:Conditions NotBefore="2024-12-01T12:00:00Z" NotOnOrAfter="2024-12-01T12:10:00Z">
      <saml:AudienceRestriction>
        <saml:Audience>https://app.example.com</saml:Audience>
      </saml:AudienceRestriction>
    </saml:Conditions>
    
    <saml:AttributeStatement>
      <saml:Attribute Name="email">
        <saml:AttributeValue>alice@example.com</saml:AttributeValue>
      </saml:Attribute>
    </saml:AttributeStatement>
  </saml:Assertion>
</samlp:Response>
```

### SAML Assertion Encryption

Encrypt the `<saml:Assertion>` element using AES-256-CBC (or AES-256-GCM). The symmetric key is encrypted with the SP's RSA public key. Only the SP can decrypt it.

```xml
<saml:EncryptedAssertion>
  <xenc:EncryptedData Type="http://www.w3.org/2001/04/xmlenc#Element">
    <xenc:EncryptionMethod Algorithm="http://www.w3.org/2001/04/xmlenc#aes256-cbc"/>
    <ds:KeyInfo>
      <xenc:EncryptedKey>
        <xenc:EncryptionMethod Algorithm="http://www.w3.org/2001/04/xmlenc#rsa-oaep-mgf1p"/>
        <xenc:CipherData><xenc:CipherValue>...</xenc:CipherValue></xenc:CipherData>
      </xenc:EncryptedKey>
    </ds:KeyInfo>
    <xenc:CipherData><xenc:CipherValue>...</xenc:CipherValue></xenc:CipherData>
  </xenc:EncryptedData>
</saml:EncryptedAssertion>
```

**Library recommendation**: Use a well-vetted SAML library — never implement XML Digital Signature validation yourself. `node-saml`, `python3-saml`, `java-saml` (by Okta), `ruby-saml`.

---

## JWT Deep Dive

### Structure

```
header.payload.signature

Header (base64url-encoded JSON):
{
  "alg": "RS256",
  "typ": "JWT",
  "kid": "key-id-2024-01"  // key ID for JWKS rotation
}

Payload (base64url-encoded JSON):
{
  "sub": "user:123",
  "iss": "https://auth.example.com",
  "aud": "my-api",
  "exp": 1734567890,
  "iat": 1734564290,
  "jti": "unique-token-id"  // JWT ID for replay prevention
}

Signature:
RS256: RSASSA-PKCS1-v1_5(SHA-256, base64url(header) + "." + base64url(payload), privateKey)
```

### Signing Algorithms

**RS256 (RSA + SHA-256)**: Asymmetric. AS signs with private key; resource servers verify with public key from JWKS endpoint. Public key can be distributed safely — resource servers never see the private key. **Preferred for distributed systems.**

**ES256 (ECDSA + P-256 + SHA-256)**: Asymmetric. Smaller signatures than RS256; equivalent security. P-256 is NIST-approved. Preferred when bandwidth is a concern (mobile, IoT).

**HS256 (HMAC + SHA-256)**: Symmetric. Single shared secret between signer and verifier. If the resource server is compromised, it can forge tokens (it has the signing key). **Avoid in distributed systems where the resource server is a different service.** Acceptable only when AS and RS are the same process.

**alg: none attack**: Some JWT libraries historically accepted `"alg": "none"` (unsigned tokens). Always reject tokens with `alg: none` or `alg: RS256` when you expect `HS256`. Explicitly configure accepted algorithms in your JWT library — do not use the algorithm from the token header without validation.

### Claims Validation (Order Matters)

```typescript
import { jwtVerify, createRemoteJWKSet } from 'jose'; // npm: jose

const JWKS = createRemoteJWKSet(new URL('https://auth.example.com/.well-known/jwks.json'));

async function validateToken(token: string): Promise<JWTPayload> {
  const { payload } = await jwtVerify(token, JWKS, {
    issuer: 'https://auth.example.com',     // validates iss
    audience: 'my-api',                      // validates aud
    algorithms: ['RS256', 'ES256'],          // reject all others
    clockTolerance: 30,                      // 30 seconds clock skew allowance
  });
  
  // Additional claims validation
  if (!payload.sub) throw new Error('Missing sub claim');
  
  return payload;
}
```

### JWKS Key Rotation Without Downtime

```
1. Generate new key pair (new private key + public key)
2. Add new public key to JWKS endpoint WITH a new "kid" (key ID)
   (Both old and new public keys are in JWKS now)
3. Update AS to sign new tokens with new private key (new kid in header)
4. Wait for all tokens signed with old key to expire (one access token lifetime)
5. Remove old public key from JWKS
```

Resource servers must:
- Cache JWKS but re-fetch when they encounter a `kid` they don't have
- Never hardcode JWKS — always fetch from `jwks_uri`

---

## API Keys

### Generation

```typescript
// Cryptographically random, 256-bit (32 bytes) minimum
import { randomBytes } from 'crypto';

function generateApiKey(): { prefix: string; plaintext: string; hash: string } {
  const prefix = 'sk'; // scannable prefix — helps identify key type in logs
  const raw = randomBytes(32).toString('base64url'); // 43 characters
  const plaintext = `${prefix}_${raw}`; // sk_abc123...
  
  // Hash for storage — never store plaintext
  const hash = createHash('sha256').update(plaintext).digest('hex');
  
  return { prefix, plaintext, hash };
}

// Store hash in DB, return plaintext to user ONCE (at creation)
// User sees: sk_abc123... (never again)
// DB stores: sha256:a3f8b2c9...
```

**Why bcrypt/Argon2 for API keys?**: API key lookup is a hot path — bcrypt is slow by design (that's the point for passwords). For API keys, SHA-256 is acceptable because keys are already high-entropy (not guessable from a dictionary). Use bcrypt/Argon2 only for user passwords (low-entropy secrets).

### Key Prefix for Scanability

Prefixes (e.g., `sk_`, `pk_`, `rk_`) make it easy to identify and invalidate keys in git history, logs, or Slack messages. GitHub's secret scanning uses this pattern — they scan repos for known vendor key prefixes.

### Key Rotation Workflow

```
1. User requests new key (keeps old key active)
2. System issues new key, sets old key's revoke_at = NOW() + grace_period
3. User updates their systems with new key
4. At revoke_at, old key is deactivated
5. Any requests with old key return 401 with "key expired, please rotate" message
```

---

## Mutual TLS (mTLS)

Standard TLS authenticates the server to the client (client verifies server certificate). mTLS also authenticates the client to the server.

### Certificate Generation

```bash
# 1. Create CA (Certificate Authority) — self-signed for internal use
openssl genrsa -out ca.key 4096
openssl req -new -x509 -days 3650 -key ca.key -out ca.crt \
  -subj "/CN=Internal CA/O=MyCompany"

# 2. Create server certificate
openssl genrsa -out server.key 2048
openssl req -new -key server.key -out server.csr \
  -subj "/CN=api.example.com"
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key \
  -CAcreateserial -out server.crt -days 365

# 3. Create client certificate (for Service A)
openssl genrsa -out client.key 2048
openssl req -new -key client.key -out client.csr \
  -subj "/CN=service-a/O=MyCompany"
openssl x509 -req -in client.csr -CA ca.crt -CAkey ca.key \
  -CAcreateserial -out client.crt -days 365
```

### NGINX mTLS Configuration

```nginx
server {
  listen 443 ssl;
  ssl_certificate /etc/nginx/ssl/server.crt;
  ssl_certificate_key /etc/nginx/ssl/server.key;
  ssl_client_certificate /etc/nginx/ssl/ca.crt;
  ssl_verify_client on;       # require client certificate
  ssl_verify_depth 2;         # allow intermediate CAs

  # Forward client identity to upstream
  proxy_set_header X-SSL-Client-CN $ssl_client_s_dn_cn;
}
```

### SPIFFE/SPIRE for Automated Identity

SPIFFE (Secure Production Identity Framework For Everyone) provides a standard for workload identity in dynamic cloud-native environments.

```
SPIRE Server: Manages the identity registry
SPIRE Agent: Runs on each node; attests workloads; issues SVIDs

SVID (SPIFFE Verifiable Identity Document):
  - x.509 SVID: An X.509 certificate with URI SAN = spiffe://trust-domain/service/name
    Example: spiffe://example.com/service/order-service
  - JWT SVID: A JWT with sub = the SPIFFE ID
```

```bash
# Workload (service) fetches its SVID from SPIRE Agent via Workload API
# Automatic rotation before expiry (default cert lifetime: 1 hour)
# No long-lived secrets — identity is attestation-based (process/container/Kubernetes attributes)
```

SPIRE is the reference implementation of SPIFFE. Istio uses SPIFFE SVIDs for mTLS between services.

---

## FIDO2 / WebAuthn

WebAuthn allows authentication using platform authenticators (fingerprint, Face ID) or roaming authenticators (YubiKey) — eliminating passwords entirely. "Passkeys" are synced WebAuthn credentials (iOS Keychain, Google Password Manager).

### Authenticator Types

- **Platform authenticator**: Built into the device — Touch ID, Face ID, Windows Hello. Credential is tied to this device (or synced if passkey).
- **Cross-platform (roaming) authenticator**: External device — YubiKey, FIDO2 USB security key. Works on any computer.

### Registration Flow (Credential Creation)

```javascript
// 1. Server generates challenge
const options = await server.generateRegistrationOptions({
  rpName: 'My App',
  rpID: 'app.example.com',
  userID: userId,
  userName: userEmail,
  attestationType: 'none',  // 'none' | 'indirect' | 'direct'
  authenticatorSelection: {
    residentKey: 'required',       // passkey — credential stored on authenticator
    userVerification: 'required',  // require biometric/PIN
  },
});

// 2. Browser calls WebAuthn API
const credential = await navigator.credentials.create({ publicKey: options });

// 3. Send credential to server for verification and storage
await server.verifyRegistrationResponse({
  response: credential,
  expectedChallenge: options.challenge,
  expectedOrigin: 'https://app.example.com',
  expectedRPID: 'app.example.com',
});
// Server stores: credentialID, publicKey, counter (for clone detection)
```

### Authentication Flow (Assertion)

```javascript
// 1. Server generates challenge (fresh per request)
const options = await server.generateAuthenticationOptions({
  rpID: 'app.example.com',
  userVerification: 'required',
});

// 2. Browser calls WebAuthn API
const assertion = await navigator.credentials.get({ publicKey: options });

// 3. Server verifies:
await server.verifyAuthenticationResponse({
  response: assertion,
  expectedChallenge: options.challenge,
  expectedOrigin: 'https://app.example.com',
  expectedRPID: 'app.example.com',
  authenticator: storedCredential, // fetched from DB by credentialID
  requireUserVerification: true,
});
// Server MUST verify counter > stored counter (prevents cloned authenticator reuse)
```

**RP ID**: Must be a registrable domain suffix of the page's origin. `app.example.com` can use `rpID: 'app.example.com'` or `rpID: 'example.com'`. Setting `rpID: 'example.com'` allows credentials to work on all subdomains.

### Attestation

Attestation allows the server to verify that the credential was created on a specific authenticator model (e.g., genuine YubiKey). Three modes:
- `none`: Skip attestation — simplest, most compatible, no device verification
- `indirect`: AS can modify attestation statement — less trust
- `direct`: Raw authenticator attestation — verify against FIDO Metadata Service (MDS)

For most applications, `none` is appropriate — passkey authentication is already far stronger than passwords regardless of attestation.

---

## Session Management

### Cookie Attributes

```http
Set-Cookie: sessionId=abc123;
  HttpOnly;          ← JavaScript cannot read (XSS protection — mandatory)
  Secure;            ← HTTPS only (mandatory in production)
  SameSite=Strict;   ← Cookie not sent on cross-site requests (CSRF protection)
  Path=/;
  Max-Age=3600;      ← Expire after 1 hour
  Domain=.example.com
```

**SameSite values**:
- `Strict`: Cookie never sent on cross-site requests — strongest CSRF protection; breaks OAuth redirect flows
- `Lax`: Cookie sent on top-level navigation (GET only) — good balance; default in modern browsers
- `None`: Cookie sent on all cross-site requests — requires `Secure`; only for third-party contexts (e.g., embedded iframes, OAuth flows)

### Session ID Requirements

- Minimum 128 bits of entropy (e.g., 16 cryptographically random bytes)
- `crypto.randomBytes(16).toString('hex')` in Node.js
- UUID v4 is 122 bits — acceptable but prefer explicit 128-bit generation

### Session Fixation Prevention

Session fixation: attacker sets a known session ID before authentication; victim logs in; attacker now has an authenticated session.

**Prevention**: Regenerate the session ID on every privilege escalation (login, role change, password change).

```typescript
// Express + express-session
app.post('/login', async (req, res) => {
  const user = await authenticate(req.body);
  if (!user) return res.status(401).json({ error: 'Invalid credentials' });
  
  // Regenerate session ID — prevents session fixation
  req.session.regenerate((err) => {
    if (err) return next(err);
    req.session.userId = user.id;
    req.session.role = user.role;
    res.json({ success: true });
  });
});
```

### CSRF Protection

**Double Submit Cookie pattern**: Set a CSRF token in a cookie (readable by JS, NOT httpOnly) and require the same value in a request header. The attacker's page cannot read the cookie (SameSite + CORS) and therefore cannot set the header.

```typescript
// Set CSRF cookie on page load
res.cookie('csrf-token', generateCSRFToken(), {
  secure: true,
  sameSite: 'Strict',
  // NOT httpOnly — JS must read it to copy to header
});

// Middleware: validate CSRF
app.use((req, res, next) => {
  if (['GET', 'HEAD', 'OPTIONS'].includes(req.method)) return next();
  
  const cookieToken = req.cookies['csrf-token'];
  const headerToken = req.headers['x-csrf-token'];
  
  if (!cookieToken || cookieToken !== headerToken) {
    return res.status(403).json({ error: 'CSRF validation failed' });
  }
  next();
});
```

**Synchronizer Token Pattern**: Store CSRF token server-side in the session. More secure than Double Submit but requires stateful sessions.

---

## RBAC vs ABAC vs ReBAC

### RBAC (Role-Based Access Control)

Users are assigned roles; roles have permissions.

```
User → Roles: [admin, editor]
Role admin → Permissions: [read:*, write:*, delete:*]
Role editor → Permissions: [read:articles, write:articles]
```

**Role explosion**: As fine-grained control grows, role combinations explode. 50 roles × 20 resources = impractical.

### ABAC (Attribute-Based Access Control)

Decisions based on attributes of the subject (user), object (resource), action, and environment.

```python
# OPA (Open Policy Agent) Rego policy
package authz

allow {
  input.action == "read"
  input.resource.owner == input.user.id  # user can read their own resources
}

allow {
  input.user.role == "admin"  # admins can read anything
  input.action == "read"
}

allow {
  input.user.department == input.resource.department  # same department
  input.action == "read"
}
```

```bash
# OPA evaluation
curl -X POST http://localhost:8181/v1/data/authz/allow \
  -d '{"input": {"user": {"id": "u1", "role": "editor"}, "action": "read", "resource": {"owner": "u1"}}}'
```

### ReBAC (Relationship-Based Access Control)

Access determined by the graph of relationships between subjects and objects. Google Zanzibar is the canonical implementation. SpiceDB and OpenFGA are open-source implementations.

```
# Zanzibar/SpiceDB tuple model
document:readme#owner@user:alice        ← alice is an owner of readme
document:readme#viewer@user:bob         ← bob is a viewer of readme
document:readme#viewer@group:engineering#member  ← engineering group members are viewers

# Check API
check(user:alice, "editor", document:readme)     → TRUE (owner implies editor)
check(user:bob, "editor", document:readme)       → FALSE (viewer cannot edit)
check(user:charlie, "viewer", document:readme)   → TRUE (if charlie is in engineering group)
```

ReBAC excels at: Google Drive-like sharing, GitHub repo permissions, social network privacy settings.

---

## Keycloak Configuration

```bash
# Realm creation via Admin REST API
curl -X POST http://localhost:8080/admin/realms \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"realm": "my-realm", "enabled": true}'

# Client setup
curl -X POST http://localhost:8080/admin/realms/my-realm/clients \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{
    "clientId": "my-app",
    "protocol": "openid-connect",
    "publicClient": false,
    "redirectUris": ["https://app.example.com/callback"],
    "webOrigins": ["https://app.example.com"]
  }'
```

**Protocol Mappers**: Add custom claims to tokens (e.g., user's internal ID, tenant, custom roles). Configure under Client → Client Scopes → Mappers.

**Custom Authenticators**: Implement `org.keycloak.authentication.Authenticator` Java interface; deploy as a Keycloak SPI provider; configure in Authentication Flows.

---

## AWS Cognito

### User Pool vs Identity Pool

- **User Pool**: Manages user directory and authentication. Issues JWT tokens (ID token, access token, refresh token). Handles sign-up, sign-in, MFA, password policies.
- **Identity Pool**: Exchanges tokens (from User Pool, Google, Facebook, SAML) for temporary AWS credentials (STS). Enables direct AWS service access from client.

### Pre-Token Generation Lambda

Runs before Cognito issues tokens — allows adding/modifying claims:

```python
def handler(event, context):
    # Add custom claim to ID token and access token
    event['response'] = {
        'claimsAndScopeOverrideDetails': {
            'idTokenGeneration': {
                'claimsToAddOrOverride': {
                    'tenant_id': get_tenant_for_user(event['userName'])
                }
            }
        }
    }
    return event
```

---

## Zero-Trust Identity

Traditional security: "trust everything inside the network perimeter." Zero-trust: **never trust, always verify** — regardless of network location.

**Principles**:
1. Verify explicitly — authenticate and authorize every request using all available signals (identity, device, location, service)
2. Use least privilege — minimize access scope; time-bound access; JIT (just-in-time) provisioning
3. Assume breach — design for containment; segment access; log everything; detect anomalies

**Implementation building blocks**:
- Strong identity for every workload (SPIFFE/SPIRE for services; mTLS between services)
- Strong identity for every user (MFA, WebAuthn/FIDO2, short-lived session tokens)
- Device posture (device health certificates, MDM enrollment check before granting access)
- Continuous validation (not just on login — re-validate throughout the session)
- Micro-segmentation (network policies deny all by default; Kubernetes NetworkPolicy; Istio AuthorizationPolicy)

---

## Anti-Hallucination Protocol

**Verify before asserting:**
1. OAuth 2.0 RFC is RFC 6749; PKCE is RFC 7636; JWT is RFC 7519; JWK is RFC 7517; Bearer Token Usage is RFC 6750 — verify specific claims against the actual RFC text at `rfc-editor.org`
2. PKCE `S256` method: `code_challenge = BASE64URL(SHA256(ASCII(code_verifier)))` — not SHA512, not raw bytes. Verify formula against RFC 7636 Section 4.2.
3. `SameSite=Strict` does NOT send cookies on top-level cross-site navigations (e.g., clicking a link from another site). `SameSite=Lax` allows top-level GET navigations. This behavioral difference breaks OAuth redirect flows with Strict.
4. WebAuthn `rpID` must be a registrable domain suffix — not any arbitrary string. Verified against the Web Authentication API spec at `w3.org/TR/webauthn-2/`
5. SAML InResponseTo: the SP MUST store outstanding AuthnRequest IDs and verify InResponseTo. If this check is skipped, IdP-initiated attacks are possible. This is a real, documented SAML vulnerability.
6. JWT `alg: none` vulnerability: not all libraries are vulnerable — modern libraries reject it by default. Do not claim "JWT is insecure" — the spec and modern implementations handle this. Verify your specific library's default behavior.
7. SPIFFE trust domain is the URI prefix `spiffe://trust-domain/...` — not a URL, not an email address. SVID URIs are `spiffe://`, not `https://`.
8. AWS Cognito User Pool tokens: ID Token contains user claims; Access Token is used to authorize Cognito API calls; NOT for authorizing your own API (use ID Token or a separate custom JWT). Access Token claims are minimal by default.
9. bcrypt max input length is 72 bytes — passwords longer than 72 bytes are silently truncated. For API key hashing, use SHA-256 (no length limit). For user passwords, pre-hash with SHA-256 then bcrypt to avoid truncation, or use Argon2id (no length limit).
10. OpenFGA is an open-source implementation of Google Zanzibar. SpiceDB (by Authzed) is another. They have different query APIs — do not conflate them.

---

## Self-Review Checklist

Before delivering any authentication or authorization solution, verify:

- [ ] **Algorithm pinned**: JWT validation explicitly specifies accepted algorithms — does not trust `alg` claim in token header blindly
- [ ] **All ID token claims validated**: `iss`, `aud`, `exp`, `iat`, `nonce` (if OIDC) — in that order; not just expiry
- [ ] **PKCE implemented**: All authorization code flows from browser or mobile clients use `code_challenge_method=S256`
- [ ] **State parameter validated**: CSRF state parameter from OAuth flow verified against session storage before token exchange
- [ ] **Refresh token rotation**: Old token invalidated when new one issued; reuse detection implemented
- [ ] **Session regenerated on login**: `session.regenerate()` called immediately after successful authentication
- [ ] **Cookie attributes**: `HttpOnly`, `Secure`, `SameSite` all set appropriately; domain scope minimal
- [ ] **Token storage**: Access tokens in memory (not localStorage); refresh tokens in httpOnly cookie or server-side session
- [ ] **Revocation considered**: Short-lived access tokens OR token blocklist for revocation; explicitly decided
- [ ] **SAML replay prevention**: `InResponseTo` verified; assertion `jti`/ID stored and checked for replay
- [ ] **mTLS certificate rotation**: Certificates have expiry; rotation process defined and tested before expiry
- [ ] **Secrets not hardcoded**: No client_secret, private keys, or HMAC secrets in source code or Docker images
- [ ] **Scope principle of least privilege**: Tokens request only the scopes required for the operation
- [ ] **Rate limiting on auth endpoints**: `/token`, `/authorize`, `/login` protected against brute force; lockout or CAPTCHA after N failures
- [ ] **Logging without secrets**: Auth events logged (login, logout, token issuance, failure) but never log tokens, passwords, or secrets
