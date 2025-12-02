# GCP Cloud Run Deployment Plan

## Overview

This plan sets up automated deployment from GitHub to Google Cloud Run. Every push to `main` triggers: tests → Docker build → push to Artifact Registry → deploy to Cloud Run.

**Target State:**
- App live at `canifuckingdownwindtoday.com` and `www.canifuckingdownwindtoday.com`
- Zero-downtime deployments on every push to `main`
- Secrets managed securely in GCP Secret Manager
- Scale-to-zero for cost optimization

---

## Prerequisites

Before starting, ensure you have:
- [ ] Google Cloud CLI (`gcloud`) installed and authenticated
- [ ] GitHub repository admin access
- [ ] Cloudflare account with `canifuckingdownwindtoday.com` domain
- [ ] Your `GEMINI_API_KEY` value ready

---

## Phase 1: GCP Project Setup (Manual, One-Time)

These steps configure your GCP project. Run them once from your terminal.

### Task 1.1: Enable Required APIs

**Why:** Cloud Run, Artifact Registry, Secret Manager, and IAM APIs must be enabled before use.

```bash
gcloud config set project heylane-c6002

gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  iamcredentials.googleapis.com \
  cloudresourcemanager.googleapis.com
```

**Verify:** `gcloud services list --enabled` should show all five services.

---

### Task 1.2: Create Artifact Registry Repository

**Why:** This is where Docker images are stored.

```bash
gcloud artifacts repositories create canifuckingdownwindtoday \
  --repository-format=docker \
  --location=us-east1 \
  --description="Container images for downwind app"
```

**Verify:** `gcloud artifacts repositories list --location=us-east1`

---

### Task 1.3: Store GEMINI_API_KEY in Secret Manager

**Why:** Secrets should never be in code or GitHub. Cloud Run will mount this at runtime.

```bash
echo -n "YOUR_ACTUAL_GEMINI_API_KEY" | gcloud secrets create GEMINI_API_KEY --data-file=-

# Grant Cloud Run access to read the secret
gcloud secrets add-iam-policy-binding GEMINI_API_KEY \
  --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

**Note:** Replace `PROJECT_NUMBER` with your actual project number. Find it with:
```bash
gcloud projects describe heylane-c6002 --format="value(projectNumber)"
```

**Verify:** `gcloud secrets list` shows `GEMINI_API_KEY`

---

### Task 1.4: Set Up Workload Identity Federation for GitHub Actions

**Why:** This allows GitHub Actions to authenticate to GCP without storing service account keys. It's the secure, recommended approach.

```bash
# Create a Workload Identity Pool
gcloud iam workload-identity-pools create "github-actions-pool" \
  --location="global" \
  --display-name="GitHub Actions Pool"

# Create a Provider for GitHub
gcloud iam workload-identity-pools providers create-oidc "github-provider" \
  --location="global" \
  --workload-identity-pool="github-actions-pool" \
  --display-name="GitHub Provider" \
  --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository" \
  --issuer-uri="https://token.actions.githubusercontent.com"

# Create a Service Account for deployments
gcloud iam service-accounts create github-actions-deployer \
  --display-name="GitHub Actions Deployer"

# Grant the service account necessary permissions
PROJECT_ID=heylane-c6002

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:github-actions-deployer@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:github-actions-deployer@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/artifactregistry.writer"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:github-actions-deployer@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser"

# Allow GitHub Actions to impersonate this service account
# IMPORTANT: Replace OWNER/REPO with your actual GitHub org/repo
gcloud iam service-accounts add-iam-policy-binding \
  github-actions-deployer@${PROJECT_ID}.iam.gserviceaccount.com \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github-actions-pool/attribute.repository/OWNER/REPO"
```

**Note:** Replace:
- `PROJECT_NUMBER` with your project number (from Task 1.3)
- `OWNER/REPO` with your GitHub repository (e.g., `sightama/canifuckingdownwindtoday`)

**Verify:**
```bash
gcloud iam service-accounts list
gcloud iam workload-identity-pools list --location=global
```

---

### Task 1.5: Note Values for GitHub Secrets

After completing the above, gather these values:

| Value | How to Get It | GitHub Secret Name |
|-------|---------------|-------------------|
| Project ID | `heylane-c6002` | `GCP_PROJECT_ID` |
| Project Number | `gcloud projects describe heylane-c6002 --format="value(projectNumber)"` | (used in WIF config) |
| Workload Identity Provider | `projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github-actions-pool/providers/github-provider` | `GCP_WORKLOAD_IDENTITY_PROVIDER` |
| Service Account Email | `github-actions-deployer@heylane-c6002.iam.gserviceaccount.com` | `GCP_SERVICE_ACCOUNT` |

---

## Phase 2: Create Dockerfile

### Task 2.1: Create Dockerfile

**File to create:** `Dockerfile` (project root)

**Why:** Packages the Python app into a container that Cloud Run can execute.

```dockerfile
# Use official Python slim image for smaller size
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install dependencies first (layer caching optimization)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/

# Cloud Run provides PORT env var, default to 8080
ENV PORT=8080

# Run the application (module-style for proper package resolution)
CMD ["python", "-m", "app.main"]
```

**Commit:** `feat: add Dockerfile for Cloud Run deployment`

---

### Task 2.2: Update .dockerignore

**File to modify:** `.dockerignore`

**Why:** Current .dockerignore is good but missing some items. Add docs and IDE files.

```
.venv/
__pycache__/
*.pyc
.pytest_cache/
.git/
.env
.env.example
*.log
tests/
docs/
.github/
.vscode/
*.md
LICENSE
Procfile
```

**Commit:** `chore: update .dockerignore for Cloud Run`

---

### Task 2.3: Modify app/main.py for Cloud Run Compatibility

**File to modify:** `app/main.py`

**Why:** Cloud Run sets the `PORT` environment variable. NiceGUI must bind to `0.0.0.0` (not `localhost`) and use this port.

**Current code (line 169-170):**
```python
if __name__ in {"__main__", "__mp_main__"}:
    ui.run(title='Can I Fucking Downwind Today', port=8080)
```

**Change to:**
```python
if __name__ in {"__main__", "__mp_main__"}:
    import os
    port = int(os.environ.get('PORT', 8080))
    ui.run(
        title='Can I Fucking Downwind Today',
        host='0.0.0.0',
        port=port,
        reload=False  # Disable reload in production
    )
```

**Testing:**
```bash
# Test locally with custom port
PORT=9000 python app/main.py
# Verify it runs on port 9000
```


**Commit:** `feat: make app port configurable for Cloud Run`

---

### Task 2.4: Test Docker Build Locally

**Why:** Catch build issues before pushing to CI.

```bash
# Build the image
docker build -t downwind-test .

# Run it locally (simulating Cloud Run environment)
docker run -p 8080:8080 -e GEMINI_API_KEY=your_key_here downwind-test

# Open http://localhost:8080 and verify the app works
```

**Expected behavior:** App loads, shows weather rating, toggle works.

**Commit:** None (local testing only)

---

## Phase 3: Create GitHub Actions Workflow

### Task 3.1: Create Workflow File

**File to create:** `.github/workflows/deploy.yml`

**Why:** Automates test → build → deploy on every push to main.

```yaml
name: Deploy to Cloud Run

on:
  push:
    branches:
      - main

env:
  PROJECT_ID: ${{ secrets.GCP_PROJECT_ID }}
  REGION: us-east1
  SERVICE_NAME: canifuckingdownwindtoday
  REPOSITORY: canifuckingdownwindtoday

jobs:
  test:
    name: Run Tests
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'
          cache: 'pip'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run tests
        run: pytest -v
        env:
          GEMINI_API_KEY: fake-key-for-testing

  deploy:
    name: Build and Deploy
    needs: test
    runs-on: ubuntu-latest

    permissions:
      contents: read
      id-token: write  # Required for Workload Identity Federation

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Authenticate to Google Cloud
        uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: ${{ secrets.GCP_WORKLOAD_IDENTITY_PROVIDER }}
          service_account: ${{ secrets.GCP_SERVICE_ACCOUNT }}

      - name: Set up Cloud SDK
        uses: google-github-actions/setup-gcloud@v2

      - name: Configure Docker for Artifact Registry
        run: gcloud auth configure-docker ${{ env.REGION }}-docker.pkg.dev --quiet

      - name: Build Docker image
        run: |
          docker build -t ${{ env.REGION }}-docker.pkg.dev/${{ env.PROJECT_ID }}/${{ env.REPOSITORY }}/${{ env.SERVICE_NAME }}:${{ github.sha }} .
          docker tag ${{ env.REGION }}-docker.pkg.dev/${{ env.PROJECT_ID }}/${{ env.REPOSITORY }}/${{ env.SERVICE_NAME }}:${{ github.sha }} \
                     ${{ env.REGION }}-docker.pkg.dev/${{ env.PROJECT_ID }}/${{ env.REPOSITORY }}/${{ env.SERVICE_NAME }}:latest

      - name: Push Docker image
        run: |
          docker push ${{ env.REGION }}-docker.pkg.dev/${{ env.PROJECT_ID }}/${{ env.REPOSITORY }}/${{ env.SERVICE_NAME }}:${{ github.sha }}
          docker push ${{ env.REGION }}-docker.pkg.dev/${{ env.PROJECT_ID }}/${{ env.REPOSITORY }}/${{ env.SERVICE_NAME }}:latest

      - name: Deploy to Cloud Run
        run: |
          gcloud run deploy ${{ env.SERVICE_NAME }} \
            --image=${{ env.REGION }}-docker.pkg.dev/${{ env.PROJECT_ID }}/${{ env.REPOSITORY }}/${{ env.SERVICE_NAME }}:${{ github.sha }} \
            --region=${{ env.REGION }} \
            --platform=managed \
            --allow-unauthenticated \
            --set-secrets=GEMINI_API_KEY=GEMINI_API_KEY:latest \
            --min-instances=0 \
            --max-instances=1 \
            --memory=512Mi \
            --cpu=1 \
            --timeout=60s \
            --concurrency=80

      - name: Show deployment URL
        run: |
          echo "Deployed to:"
          gcloud run services describe ${{ env.SERVICE_NAME }} --region=${{ env.REGION }} --format="value(status.url)"
```

**Commit:** `feat: add GitHub Actions workflow for Cloud Run deployment`

---

### Task 3.2: Add GitHub Secrets

**Where:** GitHub repo → Settings → Secrets and variables → Actions → New repository secret

Add these secrets:

| Secret Name | Value |
|-------------|-------|
| `GCP_PROJECT_ID` | `heylane-c6002` |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | `projects/YOUR_PROJECT_NUMBER/locations/global/workloadIdentityPools/github-actions-pool/providers/github-provider` |
| `GCP_SERVICE_ACCOUNT` | `github-actions-deployer@heylane-c6002.iam.gserviceaccount.com` |

**Verify:** All three secrets appear in the repository settings.

---

### Task 3.3: Test the Pipeline

**How:** Push a commit to `main` and watch the Actions tab.

```bash
git add .
git commit -m "ci: trigger first Cloud Run deployment"
git push origin main
```

**Expected:**
1. "Run Tests" job passes (green checkmark)
2. "Build and Deploy" job passes (green checkmark)
3. Deployment URL appears in job output

**If tests fail:** Fix the tests before proceeding. Do not skip tests.

**If deploy fails:** Check the error message. Common issues:
- Missing GitHub secrets → add them
- Permission denied → re-run Task 1.4 commands
- Image push failed → verify Artifact Registry exists (Task 1.2)

---

## Phase 4: Configure Custom Domain

### Task 4.1: Map Custom Domain in Cloud Run

**Why:** Cloud Run needs to know about your domain to provision SSL certificates.

```bash
# Map the root domain
gcloud run domain-mappings create \
  --service=canifuckingdownwindtoday \
  --domain=canifuckingdownwindtoday.com \
  --region=us-east1

# Map the www subdomain
gcloud run domain-mappings create \
  --service=canifuckingdownwindtoday \
  --domain=www.canifuckingdownwindtoday.com \
  --region=us-east1
```

**Note:** This will output DNS records you need to add to Cloudflare.

**Get the records:**
```bash
gcloud run domain-mappings describe \
  --domain=canifuckingdownwindtoday.com \
  --region=us-east1 \
  --format="yaml(resourceRecords)"
```

---

### Task 4.2: Configure Cloudflare DNS

**Where:** Cloudflare Dashboard → canifuckingdownwindtoday.com → DNS

**Add these records:**

| Type | Name | Content | Proxy Status |
|------|------|---------|--------------|
| CNAME | `@` | `ghs.googlehosted.com` | DNS only (gray cloud) |
| CNAME | `www` | `ghs.googlehosted.com` | DNS only (gray cloud) |

**Important:** Set proxy status to "DNS only" (gray cloud), not "Proxied" (orange cloud). Cloud Run handles SSL and Cloudflare proxying can interfere with certificate provisioning.

**Optional (after SSL is active):** Once certificates show `ACTIVE` status, you can switch to "Proxied" (orange cloud) for Cloudflare's DDoS protection and caching. This is optional — Cloud Run handles traffic fine without it.

**Verify:**
```bash
# Wait 5-10 minutes for DNS propagation, then:
dig canifuckingdownwindtoday.com
dig www.canifuckingdownwindtoday.com
```

---

### Task 4.3: Wait for SSL Certificate Provisioning

**Why:** Cloud Run automatically provisions SSL certificates via Let's Encrypt, but it takes time.

**Check status:**
```bash
gcloud run domain-mappings describe \
  --domain=canifuckingdownwindtoday.com \
  --region=us-east1
```

**Expected:** `certificateStatus: ACTIVE` (may take 15-30 minutes)

**Verify:** Open `https://canifuckingdownwindtoday.com` in browser. Should show your app with valid SSL.

---

## Phase 5: Update Documentation

### Task 5.1: Update README.md Deployment Section

**File to modify:** `README.md`

**Why:** Document the new deployment process for future reference.

**Replace the existing deployment section with:**

```markdown
## Deployment

This app automatically deploys to Google Cloud Run on every push to `main`.

**Live URL:** https://canifuckingdownwindtoday.com

### How It Works

1. Push to `main` triggers GitHub Actions
2. Tests run (`pytest`)
3. Docker image builds and pushes to Artifact Registry
4. Cloud Run deploys the new image
5. Zero-downtime deployment complete

### Manual Deployment (if needed)

```bash
# Build and push manually
gcloud builds submit --tag us-east1-docker.pkg.dev/heylane-c6002/canifuckingdownwindtoday/canifuckingdownwindtoday:latest

# Deploy manually
gcloud run deploy canifuckingdownwindtoday \
  --image=us-east1-docker.pkg.dev/heylane-c6002/canifuckingdownwindtoday/canifuckingdownwindtoday:latest \
  --region=us-east1
```

### Environment Variables

| Variable | Source | Description |
|----------|--------|-------------|
| `GEMINI_API_KEY` | GCP Secret Manager | API key for Gemini LLM |
| `PORT` | Cloud Run (automatic) | Port to listen on |
```

**Commit:** `docs: update README with Cloud Run deployment info`

---

## Verification Checklist

After completing all phases, verify:

- [ ] `pytest` passes locally
- [ ] Docker builds and runs locally
- [ ] Push to `main` triggers GitHub Actions
- [ ] GitHub Actions workflow completes successfully
- [ ] App is accessible at Cloud Run URL (*.run.app)
- [ ] App is accessible at `https://canifuckingdownwindtoday.com`
- [ ] App is accessible at `https://www.canifuckingdownwindtoday.com`
- [ ] SSL certificates are valid (browser shows lock icon)
- [ ] Weather data loads correctly
- [ ] Toggle between SUP/Parawing works

---

## Rollback

Cloud Run keeps previous revisions automatically. If a deployment breaks something:

```bash
# List available revisions
gcloud run revisions list --service=canifuckingdownwindtoday --region=us-east1

# Rollback to a specific revision (replace REVISION_NAME)
gcloud run services update-traffic canifuckingdownwindtoday \
  --to-revisions=REVISION_NAME=100 \
  --region=us-east1
```

You can also rollback via the Cloud Console: Cloud Run → canifuckingdownwindtoday → Revisions → select revision → "Manage Traffic".

---

## Troubleshooting

### Health Check Failures
Cloud Run performs automatic health checks by sending requests to your container's port. If the app doesn't respond within the startup timeout, the deployment fails.
- Ensure `host='0.0.0.0'` is set (not `localhost` or `127.0.0.1`)
- Ensure the app listens on the `PORT` environment variable
- Check startup logs: `gcloud run logs read --service=canifuckingdownwindtoday --region=us-east1`

### "Permission denied" in GitHub Actions
- Re-run Task 1.4, ensure `OWNER/REPO` matches exactly
- Verify GitHub secrets are set correctly

### "Image not found" during deploy
- Check Artifact Registry repository exists: `gcloud artifacts repositories list --location=us-east1`
- Verify image was pushed: `gcloud artifacts docker images list us-east1-docker.pkg.dev/heylane-c6002/canifuckingdownwindtoday`

### "Container failed to start"
- Check logs: `gcloud run logs read --service=canifuckingdownwindtoday --region=us-east1`
- Common issue: app not binding to `0.0.0.0` or wrong port

### SSL certificate stuck on "Pending"
- Verify DNS records point to `ghs.googlehosted.com`
- Ensure Cloudflare proxy is OFF (gray cloud)
- Wait up to 30 minutes

### App loads but shows "Weather data unavailable"
- Check Secret Manager secret exists: `gcloud secrets list`
- Verify Cloud Run has access: `gcloud secrets get-iam-policy GEMINI_API_KEY`

---

## Files Changed Summary

| File | Action | Purpose |
|------|--------|---------|
| `Dockerfile` | Create | Container definition |
| `.dockerignore` | Modify | Exclude unnecessary files |
| `app/main.py` | Modify | Port/host configuration |
| `.github/workflows/deploy.yml` | Create | CI/CD pipeline |
| `README.md` | Modify | Deployment documentation |

---

## Commit History (Suggested)

1. `feat: make app port configurable for Cloud Run`
2. `chore: update .dockerignore for Cloud Run`
3. `feat: add Dockerfile for Cloud Run deployment`
4. `feat: add GitHub Actions workflow for Cloud Run deployment`
5. `docs: update README with Cloud Run deployment info`
