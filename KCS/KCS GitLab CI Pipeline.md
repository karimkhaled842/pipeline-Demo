# KCS GitLab CI Pipeline — Real-World Reference Implementation

> **Source:** [`DevSecOps-Usecase`](https://github.com/ahmed-magdi2712/DevSecOps-Usecase) — A full DevSecOps pipeline integrating KCS, Cosign, SonarQube, and ArgoCD.

---

## Overview

This is a **complete, production-grade GitLab CI pipeline** with **8 stages** covering the full software supply chain security — from code linting to GitOps deployment. KCS (Kaspersky Container Security) is the image vulnerability scanner in the **Scan** stage.

### Complete Pipeline Stages

| # | Stage | Tool(s) | Purpose | KCS Relevant? |
|---|-------|---------|---------|:-------------:|
| 🔴 | **lint** | Ruff, Flake8, Mypy, Bandit, Hadolint, Checkov, yamllint, markdownlint | Code quality + IaC security | ❌ |
| 🟡 | **test** | pytest, pytest-cov, PostgreSQL 16, Redis 7 | Unit, integration & security tests (≥80% coverage) | ❌ |
| 🟠 | **sonarqube** | SonarQube Cloud (sonar-scanner) | Static code analysis & quality gate | ❌ |
| 🔵 | **build** | Kaniko + Syft | Multi-stage Docker image build + SBOM generation | ❌ |
| 🟣 | **scan** | **Kaspersky Container Security (KCS)** | Vulnerability, malware, config & secret scanning | **✅ Core** |
| 🟢 | **sign** | Cosign (key-based) | Image + SBOM signing & verification | ❌ |
| 📊 | **security-summary** | Custom script | Aggregate & report pipeline security results | ❌ |
| 🚀 | **deploy** | ArgoCD + Kustomize | GitOps deployment to Kubernetes | ❌ |

---

## 1. Main Pipeline Orchestrator — `.gitlab-ci.yml`

```yaml
---
# ==============================================================================
# GitLab CI: DevSecOps Pipeline (Main Orchestrator)
# ==============================================================================
# This is the main pipeline definition. It includes reusable templates for each
# stage and defines the overall workflow rules, variables, and stage ordering.
#
# Cross-repo usage:
#   include:
#     - project: 'ahmed-magdi2712/DevSecOps-Usecase'
#       file: '//.gitlab-ci.yml'
#       ref: main
# ==============================================================================

# ---------------------------------------------------------------------------
# Workflow Rules — determines when the pipeline runs
# ---------------------------------------------------------------------------
workflow:
  rules:
    # Push to main, develop, or release/*
    - if: '$CI_PIPELINE_SOURCE == "push" && $CI_COMMIT_BRANCH =~ /^(main|develop|release\/.*)$/'
    # Merge request targeting main
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event" && $CI_MERGE_REQUEST_TARGET_BRANCH_NAME == "main"'
    # Manual trigger
    - if: '$CI_PIPELINE_SOURCE == "web"'
    # Scheduled pipelines
    - if: '$CI_PIPELINE_SOURCE == "schedule"'
    # Default: don't run for other cases
    - when: never

# ---------------------------------------------------------------------------
# Global Variables
# ---------------------------------------------------------------------------
variables:
  IMAGE_NAME: "${CI_REGISTRY_IMAGE}"
  COSIGN_EXPERIMENTAL: "true"
  SYFT_FORMAT: spdx-json
  APP_NAME: secureapp-dev
  SONAR_HOST_URL: https://sonarcloud.io

  # Git strategy
  GIT_DEPTH: "0"
  GIT_STRATEGY: clone

# ---------------------------------------------------------------------------
# Pipeline Stages (in order) — full DevSecOps lifecycle
# ---------------------------------------------------------------------------
stages:
  - lint
  - test
  - sonarqube
  - build
  - scan              # <-- KCS scanning stage
  - sign
  - security-summary
  - deploy

# ---------------------------------------------------------------------------
# Template Includes — modular reusable workflows
# Each template can be used independently by other repos via:
#   include:
#     - project: 'ahmed-magdi2712/DevSecOps-Usecase'
#       file: '/gitlab_ci/templates/<name>.yml'
#       ref: main
# ---------------------------------------------------------------------------
include:
  - local: templates/lint.yml
  - local: templates/test.yml
  - local: templates/sonarqube.yml
  - local: templates/build.yml
  - local: templates/scan.yml           # <-- KCS scanner integration
  - local: templates/sign.yml
  - local: templates/security-summary.yml
  - local: templates/deploy.yml
```

---

## 2. Stage: Lint — `templates/lint.yml`

**Purpose:** Code quality, style, and static application security testing (SAST).

```yaml
---
# ==============================================================================
# Template: Lint
# ==============================================================================
# Performs comprehensive linting across multiple languages and frameworks:
#   - Python: ruff, flake8, mypy, bandit, pydocstyle, isort
#   - Docker: hadolint
#   - YAML: yamllint
#   - Markdown: markdownlint
#   - IaC: Checkov (Kubernetes security scanning)
# ==============================================================================

lint:
  stage: lint
  image: python:3.12
  tags:
    - k8s
  interruptible: true

  before_script:
    # Upgrade pip and install Python linting tools
    - pip install --upgrade pip
    - pip install -r src/app/requirements.txt
    - pip install ruff flake8 mypy bandit pylint pydocstyle black isort lxml yamllint

    # Install hadolint (Dockerfile linter)
    - |
      HADOLINT_VER=$(curl -sL https://api.github.com/repos/hadolint/hadolint/releases/latest | grep tag_name | cut -d'"' -f4)
    - |
      wget -q "https://github.com/hadolint/hadolint/releases/download/${HADOLINT_VER}/hadolint-Linux-x86_64" -O /usr/local/bin/hadolint
    - chmod +x /usr/local/bin/hadolint

    # Install markdownlint-cli2
    - apt-get update && apt-get install -y --no-install-recommends nodejs npm
    - npm install -g markdownlint-cli2

    # Install Checkov (IaC security)
    - pip install checkov

  script:
    # ---- Python Linters ----
    - echo "=== Ruff (Fast Python Linter) ==="
    - ruff check src/ --exit-zero
    - ruff format --check src/ --diff || true

    - echo "=== Flake8 ==="
    - flake8 src/ --exit-zero --max-line-length=120 --ignore=E501,W503,E203

    - echo "=== Mypy (Type Checking) ==="
    - mypy src/ --ignore-missing-imports --no-error-summary --html-report=mypy-report || true

    - echo "=== Bandit (Security Linting) ==="
    - bandit -r src/ -f json -o bandit-report.json || true
    - bandit -r src/ -ll || true

    - echo "=== pydocstyle (Documentation Linting) ==="
    - pydocstyle src/ --convention=pep257 --add-ignore=D100,D101,D102,D103,D104,D105,D107 || true

    - echo "=== isort (Import Sorting) ==="
    - isort --check-only --diff src/ || true

    # ---- Dockerfile Lint ----
    - echo "=== hadolint (Dockerfile Linting) ==="
    - hadolint docker/Dockerfile --failure-threshold warning

    # ---- IaC Security ----
    - echo "=== Checkov (IaC Security) ==="
    - checkov -d k8s/ --framework kubernetes --output sarif --quiet || true

    # ---- YAML Lint ----
    - echo "=== yamllint ==="
    - yamllint . --no-warnings || true

    # ---- Markdown Lint ----
    - echo "=== markdownlint ==="
    - markdownlint-cli2 "**/*.md" "#node_modules" "#.github" || true

  artifacts:
    paths:
      - bandit-report.json
      - mypy-report/
      - checkov-results.sarif
    expire_in: 30 days
    when: always
```

### Tools Breakdown

| Tool | Category | What It Checks |
|------|----------|----------------|
| **Ruff** | Python linter | Style, errors, complexity (replaces Flake8 + isort) |
| **Flake8** | Python linter | PEP 8 compliance |
| **Mypy** | Type checker | Static type correctness |
| **Bandit** | SAST | Security vulnerabilities in Python code |
| **Pydocstyle** | Docs | Docstring convention compliance |
| **Hadolint** | Dockerfile | Dockerfile best practices & security |
| **Checkov** | IaC SAST | Kubernetes manifest security (CIS benchmarks) |
| **yamllint** | YAML | YAML syntax and style |
| **markdownlint** | Markdown | Documentation formatting |

---

## 3. Stage: Test — `templates/test.yml`

**Purpose:** Unit, integration, and security tests with PostgreSQL + Redis service containers and coverage enforcement.

```yaml
---
# ==============================================================================
# Template: Test
# ==============================================================================
# Runs unit tests, integration tests, and security tests with:
#   - PostgreSQL 16 (service container)
#   - Redis 7 (service container)
#   - pytest with coverage
#   - Native JUnit test reporting
# ==============================================================================

test:
  stage: test
  image: python:3.12
  interruptible: true
  needs: [lint]
  tags:
    - k8s

  # Service containers
  services:
    - name: postgres:16-alpine
      alias: postgres
      variables:
        POSTGRES_USER: test_user
        POSTGRES_PASSWORD: test_password
        POSTGRES_DB: test_db
    - name: redis:7-alpine
      alias: redis

  variables:
    DATABASE_URL: postgresql://test_user:test_password@postgres:5432/test_db
    REDIS_URL: redis://redis:6379/0
    ENVIRONMENT: testing
    COVERAGE_THRESHOLD_UNIT: "80"
    COVERAGE_THRESHOLD_INTEGRATION: "70"

  before_script:
    - pip install --upgrade pip
    - pip install -r src/app/requirements.txt
    - pip install pytest pytest-cov pytest-asyncio==0.21.2 pytest-mock \
        pytest-xdist pytest-timeout factory-boy faker \
        pytest-postgres pytest-redis httpx

  script:
    - echo "=== Unit Tests with Coverage ==="
    - |
      pytest src/app/tests/ \
        --cov=src/app \
        --cov-report=xml:coverage.xml \
        --cov-report=html:htmlcov \
        --cov-report=term-missing \
        --cov-fail-under=${COVERAGE_THRESHOLD_UNIT} \
        -v --tb=short \
        --junitxml=junit-results.xml \
        --timeout=60

    - echo "=== Integration Tests ==="
    - |
      pytest src/app/tests/integration/ \
        --cov=src/app \
        --cov-report=xml:integration-coverage.xml \
        --cov-append \
        --cov-fail-under=${COVERAGE_THRESHOLD_INTEGRATION} \
        -v --tb=short \
        --junitxml=integration-junit.xml \
        -m integration

    - echo "=== Security Tests ==="
    - |
      pytest src/app/tests/security/ \
        -v --tb=short \
        --junitxml=security-junit.xml \
        -m security

  artifacts:
    paths:
      - coverage.xml
      - integration-coverage.xml
      - htmlcov/
    reports:
      junit:
        - junit-results.xml
        - integration-junit.xml
        - security-junit.xml
    expire_in: 30 days
    when: always
```

### Key Features

| Feature | Implementation |
|---------|---------------|
| **Unit tests** | Main app tests, ≥80% coverage threshold |
| **Integration tests** | Real PostgreSQL + Redis via service containers, ≥70% coverage |
| **Security tests** | Dedicated `-m security` marker for security-focused test cases |
| **Coverage enforcement** | Pipeline fails below threshold (`--cov-fail-under`) |
| **JUnit reports** | Native GitLab merge request integration |
| **Service containers** | PostgreSQL 16 and Redis 7 auto-provisioned per job |

---

## 4. Stage: SonarQube — `templates/sonarqube.yml`

**Purpose:** Static code analysis with quality gate enforcement.

```yaml
---
# ==============================================================================
# Template: SonarQube Scan
# ==============================================================================
# Performs SonarQube analysis with:
#   - SonarQube Cloud (via sonar-scanner CLI)
#   - Quality Gate validation
#   - Metrics publishing (bugs, vulnerabilities, coverage, etc.)
#
# Prerequisites:
#   SONAR_TOKEN: (masked) SonarQube authentication token
# ==============================================================================

sonarqube:
  stage: sonarqube
  image: python:3.12
  interruptible: true
  needs: [test]

  variables:
    SONAR_HOST_URL: https://sonarcloud.io
    SONAR_SCANNER_VERSION: "6.2.1.4610"

  before_script:
    - pip install --upgrade pip
    - pip install -r src/app/requirements.txt
    - |
      SONAR_URL="https://binaries.sonarsource.com/Distribution/sonar-scanner-cli/sonar-scanner-cli-${SONAR_SCANNER_VERSION}-linux-x64.zip"
      wget -q "${SONAR_URL}"
    - unzip -q "sonar-scanner-cli-${SONAR_SCANNER_VERSION}-linux-x64.zip"
    - export PATH="$PWD/sonar-scanner-${SONAR_SCANNER_VERSION}-linux-x64/bin:$PATH"
    - sonar-scanner --version

  script:
    - echo "=== SonarQube Scan ==="
    - |
      sonar-scanner \
        -Dsonar.host.url="${SONAR_HOST_URL}" \
        -Dsonar.token="${SONAR_TOKEN}" \
        -Dsonar.projectBaseDir=. \
        -Dsonar.scm.revision="${CI_COMMIT_SHA}" \
        -Dsonar.qualitygate.wait=true \
        -Dsonar.qualitygate.timeout=300

    - echo "=== Publish SonarQube Metrics Summary ==="
    - |
      if [ ! -f ".scannerwork/report-task.txt" ]; then
        echo "No scannerwork report found -- skipping metrics summary"
        exit 0
      fi

      PROJECT_KEY=$(grep "^projectKey=" .scannerwork/report-task.txt | cut -d= -f2-)
      DASHBOARD_URL=$(grep "^dashboardUrl=" .scannerwork/report-task.txt | cut -d= -f2-)
      METRICS="bugs,vulnerabilities,code_smells,coverage,duplicated_lines_density,security_hotspots"

      curl -s -u "${SONAR_TOKEN}:" \
        "${SONAR_HOST_URL}/api/measures/component?component=${PROJECT_KEY}&metricKeys=${METRICS}" \
        > /tmp/sonar-metrics.json

      echo ""
      echo "============================================"
      echo "  SonarQube Analysis Results"
      echo "  Dashboard: ${DASHBOARD_URL}"
      echo "============================================"

      # Print metrics using Python
      printf '%s\n' \
        'import json' \
        'with open("/tmp/sonar-metrics.json") as f:' \
        '    data = json.load(f)' \
        'seen = {}' \
        'for m in data.get("component", {}).get("measures", []):' \
        '    seen[m["metric"]] = m["value"]' \
        'bugs = seen.get("bugs", "N/A")' \
        'vulns = seen.get("vulnerabilities", "N/A")' \
        'hotspots = seen.get("security_hotspots", "N/A")' \
        'smells = seen.get("code_smells", "N/A")' \
        'coverage = seen.get("coverage", "N/A")' \
        'duplication = seen.get("duplicated_lines_density", "N/A")' \
        'print("  Bugs:              " + str(bugs))' \
        'print("  Vulnerabilities:   " + str(vulns))' \
        'print("  Security Hotspots: " + str(hotspots))' \
        'print("  Code Smells:       " + str(smells))' \
        'print("  Coverage:          " + str(coverage) + "%")' \
        'print("  Duplication:       " + str(duplication) + "%")' \
        > /tmp/print_metrics.py
      python3 /tmp/print_metrics.py

      echo "============================================"
```

**Maps to:** External SAST integration (referenced in [[KCS Implementation Plan#4.2 Integrations]]).

---

## 5. Stage: Build — `templates/build.yml`

**Purpose:** Build Docker image using Kaniko (no Docker-in-Docker required) and pass image digest downstream.

```yaml
---
# ==============================================================================
# Template: Build (Kaniko)
# ==============================================================================
build:
  stage: build
  needs: [sonarqube]
  tags:
    - k8s
  image:
    name: gcr.io/kaniko-project/executor:v1.9.0-debug
    entrypoint: [""]
  script:
    - cat /etc/gitlab-runner/certs/gitlab.demo.lab.crt >> /kaniko/ssl/certs/ca-certificates.crt
    - /kaniko/executor
      --context "${CI_PROJECT_DIR}"
      --dockerfile "${CI_PROJECT_DIR}/docker/Dockerfile"
      --destination "${CI_REGISTRY_IMAGE}:${CI_COMMIT_SHORT_SHA}"
      --compressed-caching=false
      --digest-file /tmp/image-digest
    - echo "IMAGE_DIGEST=$(cat /tmp/image-digest)" >> build.env
  artifacts:
    reports:
      dotenv: build.env
    paths:
      - build.env
```

**Maps to:** [[KCS Implementation Plan#7.2 Integration Workflow]] — the build stage that produces the image artifact for KCS scanning.

---

## 6. Stage: Scan (KCS) — `templates/scan.yml` ⭐

**Maps to:** [[KCS Implementation Plan#7.3 Required CI/CD Variables]]

This is the **core KCS integration** — the stage that connects to Kaspersky Container Security, receives policies, and scans the built image.

```yaml
---
# ==============================================================================
# Template: Image Scan with Kaspersky Container Security
# ==============================================================================
# Scans container images using Kaspersky Container Security scanner.
# Connects to KCS API, receives policies, scans image, outputs results.
# ==============================================================================

scan:
  stage: scan
  needs: [build]                          # Runs after image is built
  tags:
    - k8s                                 # Requires a Kubernetes GitLab runner
  image:
    name: repo.kcs.kaspersky.com/images/scanner:v2.4.0-with-db
    entrypoint: [""]
    pull_policy: if-not-present
  variables:
    SCAN_TARGET: ${CI_REGISTRY_IMAGE}:$CI_COMMIT_SHORT_SHA
    BUILD_NUMBER: ${CI_JOB_ID}
    BUILD_PIPELINE: ${CI_PIPELINE_ID}
    API_TOKEN: ${API_TOKEN}                # KCS API token (masked variable)
    API_CA_CERT: ${API_CA_CERT}            # KCS CA certificate (file variable)
    COMPANY_EXT_REGISTRY_USERNAME: ${COMPANY_EXT_REGISTRY_USERNAME}
    COMPANY_EXT_REGISTRY_PASSWORD: ${COMPANY_EXT_REGISTRY_PASSWORD}
    API_BASE_URL: https://kcs.demo.lab     # KCS API endpoint
    RUST_BACKTRACE: full                   # Debugging support
  script:
    # Standard scan mode
    - /bin/sh /entrypoint.sh $SCAN_TARGET --stdout > somefile.json

    # For debugging, uncomment:
    #- /bin/sh /entrypoint.sh $SCAN_TARGET --stdout --debug > somefile.json

    # For SBOM mode, uncomment this and comment the standard line:
    #- /bin/sh /entrypoint.sh $SCAN_TARGET --sbom-json --stdout > somefile.json
  artifacts:
    paths:
      - somefile.json                      # Scan results as pipeline artifact
```

### Variable Mapping to Implementation Plan

| Variable in Pipeline | Maps To (Plan §7.3) | Purpose |
|---------------------|---------------------|---------|
| `SCAN_TARGET` | `SCAN_TARGET` | Image reference (`registry/image:sha`) |
| `API_BASE_URL` | `API_BASE_URL` | KCS API endpoint (`https://kcs.demo.lab`) |
| `API_TOKEN` | `API_TOKEN` | KCS authentication token (🔒 **protected**) |
| `API_CA_CERT` | Certificate config (§7.3) | Public CA cert for HTTPS (file type variable) |
| `BUILD_NUMBER` | `BUILD_NUMBER` | CI job ID |
| `BUILD_PIPELINE` | `BUILD_PIPELINE` | CI pipeline ID |
| `COMPANY_EXT_REGISTRY_USERNAME` | `COMPANY_EXT_REGISTRY_USERNAME` | Registry auth (🔒 **protected**) |
| `COMPANY_EXT_REGISTRY_PASSWORD` | `COMPANY_EXT_REGISTRY_PASSWORD` | Registry auth (🔒 **protected**) |

### Scanner Image Details

| Attribute | Value |
|-----------|-------|
| **Image** | `repo.kcs.kaspersky.com/images/scanner:v2.4.0-with-db` |
| **Entrypoint** | `/bin/sh /entrypoint.sh` |
| **Standard output** | JSON file (`somefile.json`) — CycloneDX format |
| **Debug mode** | Add `--debug` flag for verbose output |
| **SBOM mode** | Add `--sbom-json` for lightweight vulnerability-only scan |

> [!tip] `API_CA_CERT` as a GitLab File Variable
> In GitLab, store the KCS CA certificate as a **File-type CI/CD variable** named `API_CA_CERT`. The runner creates a temporary file whose path is injected automatically.

---

## 7. Stage: Sign — `templates/sign.yml`

**Purpose:** Sign and verify container images using Cosign with private/public key pair.

```yaml
---
# ==============================================================================
# Template: Sign Image with Cosign
# ==============================================================================
sign:
  stage: sign
  needs:
    - job: build
      artifacts: true
    - job: scan
  tags:
    - k8s
  image:
    name: bitnami/cosign:latest
    entrypoint: [""]
  variables:
    COSIGN_PASSWORD: $COSIGN_PASSWORD
    DOCKER_CONFIG: /tmp/docker-config
    SSL_CERT_FILE: /tmp/ca-bundle.crt

  # Run only on main or release/* branches
  rules:
    - if: '$CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH || $CI_COMMIT_BRANCH =~ /^release\//'
    - when: never

  before_script:
    - mkdir -p /tmp/docker-config
    - echo "{\"auths\":{\"$CI_REGISTRY\":{\"auth\":\"$(echo -n $CI_REGISTRY_USER:$CI_REGISTRY_PASSWORD | base64)\"}}}" > /tmp/docker-config/config.json
    - echo "$COSIGN_PRIVATE_KEY" > /tmp/cosign.key
    - echo "$COSIGN_PUBLIC_KEY" > /tmp/cosign.pub
    - cat /etc/gitlab-runner/certs/gitlab.demo.lab.crt >> /tmp/ca-bundle.crt
    - export $(cat build.env | xargs)

  script:
    # Sign the image using the private key
    - |
      cosign sign \
        --key /tmp/cosign.key \
        --yes \
        "$CI_REGISTRY_IMAGE@$IMAGE_DIGEST"

    # Verify the signature using the public key
    - |
      cosign verify \
        --key /tmp/cosign.pub \
        "$CI_REGISTRY_IMAGE@$IMAGE_DIGEST"
```

---

## 8. Stage: Security Summary — `templates/security-summary.yml`

**Purpose:** Aggregate all pipeline stage results into a single summary report.

```yaml
---
# ==============================================================================
# Template: Security Summary
# ==============================================================================
# Generates a comprehensive security pipeline summary report:
#   - Aggregates results from all pipeline stages
#   - Displays status table (pass/fail/skip for each stage)
#   - Lists generated artifacts
# ==============================================================================

security-summary:
  stage: security-summary
  image: alpine:3.19
  needs:
    - job: lint
      optional: true
    - job: test
      optional: true
    - job: sonarqube
      optional: true
    - job: build
      optional: true
    - job: scan
      optional: true
    - job: sign
      optional: true

  rules:
    - when: always

  script:
    - echo "=== Security Pipeline Summary ==="
    - echo ""
    - echo "+---------------------------+---------------+"
    - echo "| Stage                     | Status        |"
    - echo "+---------------------------+---------------+"
    - |
      echo "| 🔴 Lint                   | (see job logs)|"
      echo "| 🟡 Test                   | (see job logs)|"
      echo "| 🟠 SonarQube              | (see job logs)|"
      echo "| 🔵 Build & SBOM           | (see job logs)|"
      echo "| 🟣 Image Scan (KCS)       | (see job logs)|"
      echo "| 🟢 Sign                   | (see job logs)|"
      echo "| 🚀 Deploy                 | (see job logs)|"
      echo "+---------------------------+---------------+"
      echo ""

    - echo "=== Artifacts Generated ==="
    - echo "- Lint Reports (Bandit, Pylint, Mypy, Checkov SARIF)"
    - echo "- Test Coverage Reports (JUnit + Cobertura)"
    - echo "- SonarQube Analysis (Quality Gate)"
    - echo "- SBOM (SPDX, CycloneDX formats)"
    - echo "- KCS Vulnerability Scan Report"
    - echo "- Container Image Signatures (Cosign)"
    - echo ""
    - echo "=== Pipeline URL ==="
    - echo "${CI_PIPELINE_URL}"
    - echo "Pipeline completed. Review individual job logs for details."

  artifacts:
    expire_in: 30 days
    when: always
```

---

## 9. Stage: Deploy — `templates/deploy.yml`

**Purpose:** GitOps deployment to Kubernetes via ArgoCD + Kustomize.

```yaml
---
# ==============================================================================
# Template: Deploy with ArgoCD
# ==============================================================================
# Deploys applications to Kubernetes via ArgoCD with:
#   - Kustomize-based manifest updates
#   - Git commit/push for manifest changes
#   - ArgoCD application sync with retry logic
#   - Health and sync status verification
#
# Prerequisites:
#   GIT_TOKEN_COMMIT: (masked) Git token with commit access
#   ARGOCD_TOKEN: (masked) ArgoCD API token
#   ARGOCD_SERVER: ArgoCD server address
# ==============================================================================

deploy:
  stage: deploy
  image: alpine:3.19
  needs: [sign, build]
  tags:
    - self-hosted

  # Deploy only on default branch (main)
  rules:
    - if: '$CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH'
    - when: never

  variables:
    ENVIRONMENT: development
    OVERLAY: dev

  before_script:
    - apk add --no-cache curl git bash jq

    # Install kubectl
    - curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
    - install -m 755 kubectl /usr/local/bin/kubectl
    - kubectl version --client

    # Install kustomize
    - curl -s "https://raw.githubusercontent.com/kubernetes-sigs/kustomize/master/hack/install_kustomize.sh" | bash
    - mv kustomize /usr/local/bin/
    - kustomize version

    # Install ArgoCD CLI
    - curl -sSL -o /usr/local/bin/argocd https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64
    - chmod +x /usr/local/bin/argocd
    - argocd version --client

    # Configure git with commit token
    - git remote set-url origin "https://${GIT_TOKEN_COMMIT}@${CI_SERVER_HOST}/${CI_PROJECT_PATH}.git"
    - git config user.name "gitlab-ci[bot]"
    - git config user.email "gitlab-ci[bot]@users.noreply.github.com"

  script:
    - echo "=== Normalize image name ==="
    - IMAGE_NAME_LOWER=$(echo "${IMAGE_NAME}" | tr '[:upper:]' '[:lower:]')
    - IMAGE_REF="${REGISTRY}/${IMAGE_NAME_LOWER}@${IMAGE_DIGEST}"
    - echo "Deploying: ${IMAGE_REF}"

    - echo "=== Setup Secrets and Project ==="
    - kustomize build k8s/vault-eso | kubectl apply -f -

    - echo "=== Update Kubernetes Manifests ==="
    - cd k8s/overlays/${OVERLAY}
    - kustomize edit set image "${REGISTRY}/${IMAGE_NAME_LOWER}=${IMAGE_REF}"
    - cd ${CI_PROJECT_DIR}

    - echo "=== Commit Manifest Changes to SCM ==="
    - git add k8s/overlays/${OVERLAY}/
    - |
      if git diff --staged --quiet; then
        echo "No manifest changes to commit"
      else
        git commit -m "chore(deploy): promote image ${IMAGE_NAME_LOWER} to ${IMAGE_DIGEST} [skip ci]

        Image       : ${IMAGE_REF}
        Actor       : ${GITLAB_USER_LOGIN}
        Pipeline    : ${CI_PIPELINE_URL}
        Commit      : ${CI_COMMIT_SHA}
        Ref         : ${CI_COMMIT_BRANCH}"
        git push origin HEAD:${CI_COMMIT_BRANCH}
      fi

    - echo "=== Port-forward ArgoCD Server ==="
    - kubectl port-forward -n argocd services/argocd-server 8080:80 &

    - echo "=== Sync ArgoCD Application ==="
    - |
      MAX_RETRIES=3
      RETRY_COUNT=0
      while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
        echo "Attempt $((RETRY_COUNT + 1)) of $MAX_RETRIES"
        if argocd app sync ${APP_NAME} \
          --server ${ARGOCD_SERVER} --auth-token ${ARGOCD_TOKEN} \
          --insecure --force --timeout 300; then
          echo "Sync initiated successfully"
          break
        fi
        RETRY_COUNT=$((RETRY_COUNT + 1))
        if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
          echo "Retrying in 30 seconds..."
          sleep 30
        fi
      done

    - echo "=== Wait for ArgoCD Sync ==="
    - |
      argocd app wait ${APP_NAME} \
        --server ${ARGOCD_SERVER} --auth-token ${ARGOCD_TOKEN} \
        --insecure --health --sync --timeout 600

    - echo "=== Get Application Status ==="
    - |
      echo ""
      echo "============================================"
      echo "  Deployment Status"
      echo "============================================"
      argocd app get ${APP_NAME} -o wide
      HEALTH=$(argocd app get ${APP_NAME} -o json | jq -r '.status.health.status')
      SYNC=$(argocd app get ${APP_NAME} -o json | jq -r '.status.sync.status')
      echo "--------------------------------------------"
      echo "  Health:  ${HEALTH}"
      echo "  Sync:    ${SYNC}"
      echo "  Image:   ${IMAGE_REF}"
      echo "============================================"

    - echo "=== Notify Deployment ==="
    - echo "Deployment completed successfully"
```

### Deploy Stage Details

| Step | Action                                         | Tool                       |
| ---- | ---------------------------------------------- | -------------------------- |
| 1    | Normalize image reference                      | Bash                       |
| 2    | Apply Vault ESO secrets                        | `kustomize` + `kubectl`    |
| 3    | Update Kustomize overlay with new image digest | `kustomize edit set image` |
| 4    | Commit manifest changes to SCM                 | `git commit` + `git push`  |
| 5    | Port-forward ArgoCD server                     | `kubectl port-forward`     |
| 6    | Sync ArgoCD application (with retry)           | `argocd app sync`          |
| 7    | Wait for health + sync status                  | `argocd app wait`          |
| 8    | Report deployment status                       | `argocd app get`           |

---

## 10. Complete Pipeline Flow

```mermaid
graph TD
    A[Code Push / MR] --> B{Branch?}
    B -->|main/develop/release| C[Lint: Code Quality & SAST]
    B -->|other| X[Skip Pipeline]

    C --> D[Test: Unit + Integration + Security]
    D --> E[SonarQube: Static Analysis & Quality Gate]

    E --> F{Build with Kaniko}
    F --> G[KCS Scan: Vulnerability & Malware Check]
    G --> H{Compliant?}

    H -->|Yes| I[Sign with Cosign]
    H -->|No| J[Pipeline Fails / Warning]

    I --> K[Security Summary]
    K --> L{Branch?}
    L -->|main| M[Deploy via ArgoCD]
    L -->|other| N[Pipeline Complete]

    M --> O[Kubernetes Cluster]
    N --> O
```

### Stage Dependencies (Needs Graph)

```
lint ──→ test ──→ sonarqube ──→ build ──→ scan ──→ sign ──→ security-summary ──→ deploy
                                               ↗
                                        (needs: build)
```

| Stage | Depends On | Condition |
|-------|-----------|-----------|
| `lint` | — | First stage |
| `test` | `lint` | Required |
| `sonarqube` | `test` | Required |
| `build` | `sonarqube` | Required |
| `scan` | `build` | Required (must have image to scan) |
| `sign` | `build` + `scan` | Both must pass |
| `security-summary` | All previous (optional) | Always runs (even if prior stages fail) |
| `deploy` | `sign` + `build` | Only on `main` branch |

---

## 11. Required GitLab CI/CD Variables (Complete)

Configure these in **Settings → CI/CD → Variables**:

### KCS Scanner Variables

| Variable | Type | Masked | Required For |
|----------|------|--------|-------------|
| `API_TOKEN` | Variable | ✅ Yes | KCS authentication (§6: scan) |
| `API_CA_CERT` | File | ❌ No | KCS CA cert for HTTPS (§6: scan) |
| `COMPANY_EXT_REGISTRY_USERNAME` | Variable | ✅ Yes | Private registry auth (§6: scan) |
| `COMPANY_EXT_REGISTRY_PASSWORD` | Variable | ✅ Yes | Private registry auth (§6: scan) |

### Image Signing Variables

| Variable | Type | Masked | Required For |
|----------|------|--------|-------------|
| `COSIGN_PRIVATE_KEY` | File | ✅ Yes | Cosign private key (§7: sign) |
| `COSIGN_PUBLIC_KEY` | File | ❌ No | Cosign public key (§7: sign) |
| `COSIGN_PASSWORD` | Variable | ✅ Yes | Key password (§7: sign) |

### SonarQube Variables

| Variable | Type | Masked | Required For |
|----------|------|--------|-------------|
| `SONAR_TOKEN` | Variable | ✅ Yes | SonarQube authentication (§4: sonarqube) |

### GitOps/Deploy Variables

| Variable | Type | Masked | Required For |
|----------|------|--------|-------------|
| `GIT_TOKEN_COMMIT` | Variable | ✅ Yes | Git commit/push (§9: deploy) |
| `ARGOCD_TOKEN` | Variable | ✅ Yes | ArgoCD API token (§9: deploy) |
| `ARGOCD_SERVER` | Variable | ❌ No | ArgoCD server address (§9: deploy) |

---

## 12. Adapting This Pipeline to Your Environment

### Changes Required Per Environment

| Parameter | This Repo (Example) | Your Value |
|-----------|--------------------|------------|
| `API_BASE_URL` | `https://kcs.demo.lab` | Your KCS Admin Console FQDN |
| Scanner image | `repo.kcs.kaspersky.com/images/scanner:v2.4.0-with-db` | Your KCS registry path |
| `API_TOKEN` | From KCS user profile | Create dedicated KCS user for CI/CD |
| `CI_REGISTRY` | GitLab internal registry | Your registry URL |
| GitLab runner tags | `k8s` | Your runner tags |
| `SONAR_HOST_URL` | `https://sonarcloud.io` | Your SonarQube server |
| `ARGOCD_SERVER` | Internal cluster address | Your ArgoCD server |
| Coverage thresholds | 80% unit / 70% integration | Your team's standards |

### Container Registry CA Certificate

If your GitLab runner uses a self-signed registry certificate:
```yaml
before_script:
  - cat /etc/gitlab-runner/certs/gitlab.demo.lab.crt >> /kaniko/ssl/certs/ca-certificates.crt
```

### SBOM Mode (KCS Lightweight)

For quicker scans that check vulnerabilities only:
```yaml
script:
  - /bin/sh /entrypoint.sh $SCAN_TARGET --sbom-json --stdout > somefile.json
```

---

> [!summary]
> This pipeline demonstrates a complete 8-stage DevSecOps pipeline with KCS at its heart. From **Lint → Test → SonarQube → Build → KCS Scan → Sign → Summary → Deploy**, every stage enforces security at a different point in the software supply chain. The KCS scanner runs immediately after the image is built, checks it against configured scanner and assurance policies, and gates the pipeline based on results. Only compliant, signed images are deployed to production via GitOps.
