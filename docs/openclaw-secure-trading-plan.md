# Secure AI Agent Workstation on AWS Lightsail

## Goal
Deploy a multi-agent AI workstation on AWS Lightsail running:
- **Claude Code CLI** (Anthropic)
- **Codex CLI** (OpenAI)
- **OpenClaw** (personal AI assistant)

With integrations to:
- **GitHub** (code read/write)
- **Telegram** (messaging interface)
- **Hyperliquid** (crypto trading)

With **cryptographic isolation** ensuring the Hyperliquid signing key is NEVER accessible to any agent.

## Core Security Principle
**"Use but never see"** - OpenClaw can trigger trades but the signing key exists in a completely separate security boundary with no network path to the agent.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        YOUR DEVICES                                 │
│              Telegram (mobile) / SSH (desktop)                      │
└─────────────────┬─────────────────────────────┬─────────────────────┘
                  │                             │
                  ▼                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     AWS LIGHTSAIL INSTANCE                          │
│                     (Ubuntu 24.04, 8GB RAM)                         │
│ ┌─────────────────────────────────────────────────────────────────┐ │
│ │                     DOCKER COMPOSE STACK                        │ │
│ │                                                                 │ │
│ │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │ │
│ │  │  OpenClaw    │  │ Claude Code  │  │  Codex CLI   │          │ │
│ │  │  (Gateway)   │  │    (CLI)     │  │   (OpenAI)   │          │ │
│ │  │              │  │              │  │              │          │ │
│ │  │ - Telegram   │  │ - GitHub     │  │ - GitHub     │          │ │
│ │  │ - Trading    │  │ - Workspace  │  │ - Workspace  │          │ │
│ │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │ │
│ │         │                 │                 │                   │ │
│ │         └────────────┬────┴─────────────────┘                   │ │
│ │                      ▼                                          │ │
│ │  ┌─────────────────────────────────────────────────────────┐   │ │
│ │  │              SHARED WORKSPACE (Volume)                   │   │ │
│ │  │  /workspace - Git repos, code, projects                  │   │ │
│ │  │  ⚠️ NO SECRETS HERE - agents can read/write              │   │ │
│ │  └─────────────────────────────────────────────────────────┘   │ │
│ └─────────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  ALLOWED OUTBOUND:                                                  │
│  ✓ GitHub API (git operations)                                      │
│  ✓ Telegram API (messaging)                                         │
│  ✓ Anthropic API (Claude)                                           │
│  ✓ OpenAI API (Codex)                                               │
│  ✓ Hyperliquid API (market data READ-ONLY)                          │
│  ✓ Trade Proxy API Gateway (execute trades)                         │
│                                                                     │
│  BLOCKED OUTBOUND:                                                  │
│  ✗ AWS Secrets Manager (no direct access)                           │
│  ✗ Lambda direct invoke                                             │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
                    (Trade requests only)
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      AWS API GATEWAY                                │
│  - Request validation                                               │
│  - Rate limiting (10 req/min)                                       │
│  - API key auth (NOT the signing key)                               │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                AWS LAMBDA (Trade Executor)                          │
│  - Checks SSM kill switch                                           │
│  - Validates: position ≤ $2,500, rate limits                        │
│  - Retrieves key from Secrets Manager                               │
│  - Signs & submits to Hyperliquid                                   │
│  - Publishes to SNS (SMS notification)                              │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    AWS SECRETS MANAGER                              │
│  🔐 Hyperliquid private key (ONLY Lambda can access)                │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Security Boundaries

### Boundary 1: Agent Containers (UNTRUSTED ZONE)

All three agents run in Docker with hardened settings:

| Agent | Access | Restrictions |
|-------|--------|--------------|
| **OpenClaw** | Telegram, Trade API, market data | Skills DISABLED, no Secrets Manager |
| **Claude Code** | GitHub, workspace, Anthropic API | No trade capability, no Secrets Manager |
| **Codex CLI** | GitHub, workspace, OpenAI API | No trade capability, no Secrets Manager |

Common restrictions for ALL agents:
- NO IAM credentials for Secrets Manager
- NO direct network path to Lambda
- Shared workspace volume (code only, no secrets)
- Can reach Trade API Gateway but CANNOT sign trades

### Boundary 2: Credential Isolation

| Credential | Where Stored | Who Can Access |
|------------|--------------|----------------|
| Hyperliquid private key | Secrets Manager | **Lambda ONLY** |
| GitHub token | Lightsail env var | Agents (read/write code) |
| Telegram bot token | Lightsail env var | OpenClaw only |
| Anthropic API key | Lightsail env var | Claude Code only |
| OpenAI API key | Lightsail env var | Codex CLI only |
| Trade API key | Lightsail env var | All agents (triggers trade) |

**Critical**: The Hyperliquid signing key is the ONLY secret in Secrets Manager. All other credentials are "use" credentials that can be rotated if compromised.

### Boundary 3: API Gateway (GATEKEEPER)
- Validates request structure
- Rate limits: 10 requests/minute
- Requires API key (NOT the signing key)
- Logs all requests to CloudWatch

### Boundary 4: Lambda (TRUSTED EXECUTOR)
- **ONLY** component with Secrets Manager access
- Checks SSM kill switch FIRST
- Validates ALL trade parameters:
  - Max position: $2,500
  - Rate limit enforcement
- Signs and submits to Hyperliquid
- Publishes SMS via SNS
- Returns confirmation (no key material in response)

### Boundary 5: Secrets Manager (VAULT)
- Hyperliquid private key encrypted with KMS
- IAM policy: **ONLY** Lambda execution role can read
- CloudTrail audit logging enabled
- Any access attempt from Lightsail → DENIED + ALERT

---

## Implementation Tasks

### Phase 1: AWS Infrastructure (Separate Account)

1. **Create dedicated VPC for Lightsail**
   - Private subnet for OpenClaw
   - NAT Gateway for outbound only
   - Security group: egress to API Gateway + Hyperliquid API only

2. **Set up Secrets Manager**
   - Store Hyperliquid private key
   - Enable CloudTrail logging
   - Create restrictive IAM policy

3. **Create Lambda Trade Executor**
   - Python/Node runtime
   - Hyperliquid SDK for signing
   - Validation logic:
     - Check SSM kill switch FIRST
     - Max position: $2,500
     - Rate limit: 10/minute
   - IAM role with Secrets Manager read-only + SSM read-only
   - SNS publish permission for SMS

4. **Create API Gateway**
   - REST API with Lambda integration
   - API key authentication
   - Request validation schema
   - Rate limiting configuration
   - WAF rules (optional)

### Phase 2: Lightsail + OpenClaw

5. **Provision Lightsail instance**
   - Ubuntu 24.04, 4GB RAM
   - Attach to VPC
   - Security group: SSH (your IP only), outbound HTTPS only

6. **Install Docker with hardening**
   ```bash
   # Non-root user
   # AppArmor/SELinux profile
   # Read-only root filesystem
   # No capabilities
   ```

7. **Deploy OpenClaw container**
   - Mount minimal config volume (read-only)
   - Disable skills: `agents.defaults.skills.enabled: false`
   - Configure sandbox: `agents.defaults.sandbox.scope: "session"`
   - Set workspace access: `agents.defaults.sandbox.workspaceAccess: "none"`

8. **Configure OpenClaw for trading**
   - Custom system prompt for crypto advice
   - Tool allowlist: only `trade_proposal` custom tool
   - API Gateway key (NOT the signing key)

### Phase 3: Trade Workflow Implementation

9. **Create trade proposal flow**
   ```
   You → "Should I long ETH?"
   OpenClaw → Analyzes market, proposes: "Long ETH 0.1 @ $3200, SL $3100"
   You → "Execute"
   OpenClaw → Calls API Gateway → Lambda validates → Signs → Submits
   OpenClaw → "Trade executed: [tx hash]"
   ```

10. **Implement confirmation requirement**
    - OpenClaw CANNOT auto-execute
    - Requires explicit "execute" or "confirm" message
    - Timeout after 5 minutes (proposal expires)

### Phase 4: Monitoring & Alerts

11. **SNS Topic + SMS Subscription**
    - Create SNS topic for trade notifications
    - Subscribe your phone number for SMS
    - Lambda publishes to SNS after EVERY trade:
      - Success: "✓ LONG ETH 0.1 @ $3200 | $250 | tx: 0x..."
      - Failure: "✗ REJECTED: Position $3000 exceeds $2500 limit"
      - Kill switch: "⛔ BLOCKED: Trading disabled by kill switch"

12. **CloudWatch alarms**
    - Lambda errors
    - API Gateway 4xx/5xx rates
    - Secrets Manager access attempts
    - SSM parameter changes (alert if kill switch toggled)

---

## Files Created

| File | Status | Purpose |
|------|--------|---------|
| `infrastructure/lib/stacks/trade-executor-stack.ts` | ✅ Created | CDK stack with API Gateway, Lambda, Secrets Manager, SSM, SNS |
| `infrastructure/lambda/trade-executor/index.ts` | ✅ Created | Lambda with validation, kill switch, rate limiting, SMS |
| `infrastructure/lambda/trade-executor/package.json` | ✅ Created | Lambda dependencies |
| `infrastructure/bin/app.ts` | ✅ Created | CDK entry point |
| `infrastructure/package.json` | ✅ Created | CDK project dependencies |
| `infrastructure/cdk.json` | ✅ Created | CDK configuration |

## Files Still Needed

| File | Purpose |
|------|---------|
| `infrastructure/tsconfig.json` | TypeScript config |
| `infrastructure/lambda/trade-executor/tsconfig.json` | Lambda TypeScript config |
| `lightsail/docker-compose.yml` | OpenClaw + agents container orchestration |
| `lightsail/Dockerfile.openclaw` | Hardened OpenClaw container |
| `lightsail/openclaw-config.yaml` | OpenClaw configuration with trade tool |

---

## Validation Checklist

### Security Boundary Tests
- [ ] From OpenClaw container, `aws secretsmanager get-secret-value` → **FAIL** (no creds)
- [ ] From OpenClaw container, direct Lambda invoke → **FAIL** (no network path)
- [ ] From OpenClaw container, `curl` Secrets Manager endpoint → **FAIL** (blocked)

### Trade Validation Tests
- [ ] Submit $3,000 position → **REJECTED** (exceeds $2,500 limit)
- [ ] Submit trade without "execute"/"confirm" → **NOT EXECUTED**
- [ ] 11 trades in 1 minute → 11th **REJECTED** (rate limit)

### Kill Switch Tests
- [ ] Set SSM `/openclaw/trading/enabled` = "false"
- [ ] Attempt any trade → **BLOCKED** with kill switch message
- [ ] Verify SMS received: "⛔ BLOCKED: Trading disabled"
- [ ] Re-enable and verify trading resumes

### Notification Tests
- [ ] Execute valid trade → SMS received within 30 seconds
- [ ] Trigger rejection → SMS received with failure reason

### Audit Tests
- [ ] CloudTrail shows ONLY Lambda accessing Secrets Manager
- [ ] CloudWatch logs contain NO key material
- [ ] SSM parameter change triggers CloudWatch alarm

---

## Cost Estimate (Monthly)

| Resource | Cost |
|----------|------|
| Lightsail 8GB | ~$40 |
| Lambda (low volume) | ~$1 |
| API Gateway | ~$3 |
| Secrets Manager | ~$0.40 |
| CloudWatch | ~$5 |
| SNS SMS (~100 msgs) | ~$1 |
| **Total** | **~$50/month** |

---

## Deployment Instructions

### Step 1: Deploy CDK Stack (AWS Side)
```bash
cd infrastructure
npm install
cd lambda/trade-executor && npm install && cd ../..

# Deploy (requires SMS phone in E.164 format)
npx cdk deploy -c smsPhoneNumber=+1234567890
```

### Step 2: Set Hyperliquid Private Key
```bash
# CRITICAL: Do this from a secure machine, NOT from Lightsail
aws secretsmanager put-secret-value \
  --secret-id openclaw/prod/hyperliquid/private-key \
  --secret-string "YOUR_PRIVATE_KEY_HERE"
```

### Step 3: Get API Key for OpenClaw
```bash
# Get the API key value (needed for OpenClaw config)
aws apigateway get-api-key --api-key <API_KEY_ID> --include-value
```

### Step 4: Provision Lightsail Instance
```bash
aws lightsail create-instances \
  --instance-names openclaw-agent \
  --availability-zone us-east-1a \
  --blueprint-id ubuntu_24_04 \
  --bundle-id medium_3_0  # 8GB RAM
```

### Step 5: Deploy OpenClaw on Lightsail
```bash
# SSH to Lightsail, then:
git clone <this-repo>
cd lightsail
docker compose up -d
```

### Step 6: Verify Security Isolation
```bash
# From inside OpenClaw container, this should FAIL:
aws secretsmanager get-secret-value --secret-id openclaw/prod/hyperliquid/private-key
# Expected: AccessDeniedException
```

---

## Confirmed Requirements

| Setting | Value |
|---------|-------|
| Max position per trade | **$2,500** |
| Kill switch | **SSM Parameter Store** (flip to disable instantly) |
| Notifications | **SMS for every trade** |
| Pairs | All Hyperliquid pairs (no whitelist restriction) |

---

## Kill Switch Implementation

```
SSM Parameter: /openclaw/trading/enabled
Value: "true" or "false"

Lambda checks this BEFORE every trade:
- If "false" → Reject with "Trading disabled by kill switch"
- If "true" → Proceed with validation

To disable all trading instantly:
aws ssm put-parameter --name /openclaw/trading/enabled --value "false" --overwrite
```
