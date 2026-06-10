---
name: god-keycloak
description: "God-level Keycloak IAM mastery. Covers Keycloak architecture (realms, clients, users, roles, groups), OIDC and SAML 2.0 configuration, client types (confidential, public, bearer-only), authentication flows and required actions, identity brokering and social login, user federation (LDAP/Active Directory), fine-grained authorization (RBAC, UMA, policies), custom SPIs (authenticators, providers), themes and branding, Keycloak Operator for Kubernetes, high-availability clustering, token management, and production hardening. Never fabricate Keycloak REST API endpoints — verify against keycloak.org/docs. Covers Keycloak 20+."
metadata:
  author: god-dev-suite
  version: '1.0'
---

# God-Level Keycloak IAM

## Anti-Hallucination Rules

- NEVER invent Keycloak Admin REST API paths — verify against the official API docs.
- NEVER confuse Keycloak client types — `confidential`, `public`, and `bearer-only` have specific meanings.
- NEVER fabricate Keycloak SPI names — `Authenticator`, `FormAction`, `EventListener`, `UserStorageProvider` are real SPIs.
- ALWAYS specify Keycloak version — significant changes between 17 (Quarkus migration), 20 (new admin console), 21+ (Organizations).
- ALWAYS distinguish realm-level vs client-level roles — they serve different purposes.

---

## 1. Core Concepts

### Realm Architecture

```
Keycloak Instance
├── Master Realm (admin only — never use for applications)
├── Production Realm
│   ├── Clients
│   │   ├── my-frontend (public, PKCE)
│   │   ├── my-backend-api (bearer-only)
│   │   └── my-admin-app (confidential)
│   ├── Users
│   │   ├── Local users (Keycloak database)
│   │   └── Federated users (LDAP/AD)
│   ├── Roles
│   │   ├── Realm roles (admin, user, moderator)
│   │   └── Client roles (my-backend-api/read, my-backend-api/write)
│   ├── Groups
│   │   ├── Engineering (inherits: user role)
│   │   ├── Platform (inherits: admin role)
│   │   └── Contractors (inherits: user role, limited scopes)
│   ├── Identity Providers
│   │   ├── Google (social login)
│   │   ├── GitHub (social login)
│   │   └── Corporate SAML (enterprise SSO)
│   └── Authentication Flows
│       ├── Browser flow (username/password + OTP)
│       ├── Direct grant (API login)
│       └── Custom registration flow
└── Staging Realm (mirror of production)
```

---

## 2. Client Configuration

### 2.1 Public Client (SPA / Mobile)

```json
{
  "clientId": "my-frontend",
  "enabled": true,
  "publicClient": true,
  "protocol": "openid-connect",
  "rootUrl": "https://app.example.com",
  "redirectUris": ["https://app.example.com/*"],
  "webOrigins": ["https://app.example.com"],
  "attributes": {
    "pkce.code.challenge.method": "S256",
    "post.logout.redirect.uris": "https://app.example.com/*"
  },
  "defaultClientScopes": ["openid", "profile", "email"],
  "optionalClientScopes": ["address", "phone", "roles"]
}
```

### 2.2 Confidential Client (Backend)

```json
{
  "clientId": "my-admin-app",
  "enabled": true,
  "publicClient": false,
  "protocol": "openid-connect",
  "secret": "generated-secret",
  "serviceAccountsEnabled": true,
  "authorizationServicesEnabled": true,
  "directAccessGrantsEnabled": false,
  "standardFlowEnabled": true
}
```

### 2.3 Token Configuration

```
Access Token:
  - Default lifetime: 5 minutes (recommended for APIs)
  - Contains: sub, realm_access.roles, resource_access.<client>.roles
  - Format: JWT (RS256 signed)

Refresh Token:
  - Default lifetime: 30 minutes (session timeout)
  - SSO Session Idle: 30 minutes
  - SSO Session Max: 10 hours

ID Token:
  - Contains: user profile (name, email, etc.)
  - Used by frontend for user display
  - NOT for API authorization (use access token)
```

---

## 3. OIDC Flows

### Authorization Code Flow with PKCE (Recommended)

```
1. Frontend generates code_verifier (random 43-128 chars)
2. Frontend computes code_challenge = BASE64URL(SHA256(code_verifier))
3. Frontend redirects to Keycloak:
   GET /realms/{realm}/protocol/openid-connect/auth
     ?client_id=my-frontend
     &response_type=code
     &redirect_uri=https://app.example.com/callback
     &scope=openid profile email
     &code_challenge={code_challenge}
     &code_challenge_method=S256
     &state={random_state}

4. User authenticates at Keycloak login page

5. Keycloak redirects back with authorization code:
   https://app.example.com/callback?code={code}&state={state}

6. Frontend exchanges code for tokens:
   POST /realms/{realm}/protocol/openid-connect/token
     grant_type=authorization_code
     &code={code}
     &redirect_uri=https://app.example.com/callback
     &client_id=my-frontend
     &code_verifier={code_verifier}

7. Keycloak returns: access_token, refresh_token, id_token
```

### Client Credentials Flow (Service-to-Service)

```bash
curl -X POST "https://keycloak.example.com/realms/production/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials" \
  -d "client_id=my-backend-service" \
  -d "client_secret=<SECRET>" \
  -d "scope=openid"
```

---

## 4. User Federation (LDAP/AD)

```json
{
  "name": "corporate-ldap",
  "providerId": "ldap",
  "providerType": "org.keycloak.storage.UserStorageProvider",
  "config": {
    "vendor": ["ad"],
    "connectionUrl": ["ldaps://ldap.corp.example.com:636"],
    "bindDn": ["cn=keycloak-reader,ou=service-accounts,dc=corp,dc=example,dc=com"],
    "bindCredential": ["***"],
    "usersDn": ["ou=users,dc=corp,dc=example,dc=com"],
    "usernameLDAPAttribute": ["sAMAccountName"],
    "rdnLDAPAttribute": ["cn"],
    "uuidLDAPAttribute": ["objectGUID"],
    "userObjectClasses": ["person,organizationalPerson,user"],
    "editMode": ["READ_ONLY"],
    "importEnabled": ["true"],
    "syncRegistrations": ["false"],
    "batchSizeForSync": ["1000"],
    "fullSyncPeriod": ["604800"],
    "changedSyncPeriod": ["86400"]
  }
}
```

---

## 5. Identity Brokering

```json
{
  "alias": "google",
  "providerId": "google",
  "enabled": true,
  "config": {
    "clientId": "<GOOGLE_CLIENT_ID>",
    "clientSecret": "<GOOGLE_CLIENT_SECRET>",
    "defaultScope": "openid email profile",
    "syncMode": "IMPORT",
    "guiOrder": "1"
  },
  "firstBrokerLoginFlowAlias": "first broker login"
}
```

---

## 6. Kubernetes Operator

```yaml
# Keycloak CR (Keycloak Operator)
apiVersion: k8s.keycloak.org/v2alpha1
kind: Keycloak
metadata:
  name: keycloak
  namespace: keycloak-system
spec:
  instances: 3
  db:
    vendor: postgres
    host: postgres-service
    usernameSecret:
      name: keycloak-db-secret
      key: username
    passwordSecret:
      name: keycloak-db-secret
      key: password
  hostname:
    hostname: keycloak.example.com
  http:
    tlsSecret: keycloak-tls
  proxy:
    headers: xforwarded

---
# KeycloakRealmImport CR
apiVersion: k8s.keycloak.org/v2alpha1
kind: KeycloakRealmImport
metadata:
  name: production-realm
spec:
  keycloakCRName: keycloak
  realm:
    realm: production
    enabled: true
    registrationAllowed: false
    bruteForceProtected: true
    failureFactor: 5
    maxFailureWaitSeconds: 900
    passwordPolicy: "length(12) and upperCase(1) and lowerCase(1) and digits(1) and specialChars(1) and notUsername()"
```

---

## 7. Production Hardening

```
Security checklist:
  □ Master realm used only for Keycloak admin — never for applications
  □ Admin console access restricted by IP or VPN
  □ Brute force protection enabled (failureFactor, waitIncrementSeconds)
  □ Password policy enforced (length, complexity, history)
  □ Content Security Policy headers configured
  □ HTTPS enforced (no HTTP in production)
  □ Token lifetimes minimized (access: 5min, refresh: 30min)
  □ Redirect URIs use exact matching (no wildcards in production)
  □ Client secrets rotated regularly
  □ Event logging enabled and forwarded to SIEM
  □ Admin audit logging enabled
  □ PKCE required for all public clients
  □ Service accounts have minimal roles
  □ Unused realms, clients, and flows removed
```

---

## Cross-Domain Connections

**Keycloak ↔ ArgoCD:** Configure ArgoCD OIDC SSO with Keycloak as the identity provider. Map Keycloak groups to ArgoCD RBAC roles.

**Keycloak ↔ Kubernetes:** Kubernetes OIDC authentication can use Keycloak as the identity provider. Configure kube-apiserver with `--oidc-issuer-url`, `--oidc-client-id`, `--oidc-groups-claim`.

**Keycloak ↔ Grafana:** Configure Grafana OAuth with Keycloak. Map Keycloak roles to Grafana org roles (Admin, Editor, Viewer).

**Keycloak ↔ API Gateway:** Kong, Envoy, and NGINX can validate Keycloak JWTs at the gateway level, offloading auth from backend services.

---

## Self-Review Checklist

- [ ] Master realm is not used for applications
- [ ] PKCE (S256) enforced for all public clients
- [ ] Token lifetimes are appropriate (access: 5min, refresh: 30min)
- [ ] Brute force protection enabled with reasonable thresholds
- [ ] Password policy enforced (length, complexity, history)
- [ ] LDAP/AD federation uses READ_ONLY edit mode
- [ ] Redirect URIs are exact (no wildcards in production)
- [ ] Client secrets stored in K8s Secrets or Vault (not in Git)
- [ ] Event logging enabled and forwarded to SIEM
- [ ] High availability: 3+ instances with external PostgreSQL
- [ ] Keycloak Operator manages lifecycle in Kubernetes
- [ ] Custom themes tested for accessibility and branding compliance
