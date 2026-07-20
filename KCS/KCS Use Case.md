# DevSecOps Use Case — KCS Configuration

> **Status:** #completed
> **Last Updated:** 2026-05-14

---

## 1. CI/CD Pipeline Integration

- Integrated KCS scanner into the GitLab CI pipeline.
- Pipeline gates image deployment based on Assurance Policy results.
- See full pipeline reference: [[KCS GitLab CI Pipeline]]

## 2. Registry Integration

- Added the container registry to KCS for automated image scanning.
- Enables KCS to pull and scan images directly from the registry.

## 3. Kubernetes Namespace & KCS Scope

- Created a dedicated Kubernetes namespace for the application.
- Created a corresponding **Scope** in KCS to manage resource boundaries.
- Assigned the scope to the **admin** user for RBAC enforcement.

## 4. Scanner Policy

- Created a Scanner Policy assigned to the default scope.
- Enabled all scan types:
  - ✅ **Vulnerabilities** — OS and application-level CVE detection
  - ✅ **Malicious code** — Kaspersky anti-malware engine
  - ✅ **Configuration errors** — Dockerfile and IaC misconfigurations
  - ✅ **Sensitive data** — Secrets, credentials, and regex-based pattern detection

## 5. Assurance Policy (CI/CD Gating)

- Created an Assurance Policy for CI/CD pipeline enforcement.
- Image is marked **non-compliant** (fails CI/CD step) if any of the following are detected:
  - **Critical vulnerabilities**
  - **Malware**
  - **Configuration errors**
  - **Sensitive data**

## 6. Runtime Policy (Admission Control)

- Created a Runtime Policy for the custom scope.
- **Mode:** Enforce
- Configured based on best practices:
  - CPU / Memory limits must be specified
  - Image tag must be specified (`latest` blocked)
  - Non-compliant images blocked
  - Root privileges, privileged mode, privilege escalation blocked
  - Host network / PID / IPC namespace access blocked
- **Excluded images:**
  - `postgres:*`
  - `redis:*`

## 7. Cosign Integration (Image Signature Verification)

- Added **Cosign** as an image signature validator in KCS integrations.
- Ensures only signed and verified images can be deployed.

## 8. Container Runtime Profile (eBPF-based)

Created a runtime profile for the application based on **auto-profiling** results.

| Feature | Configuration |
|---------|--------------|
| **File Threat Protection** | **Mode:** Enforce → Delete malicious code<br>**Scan mode:** Smart Check<br>**Options:** Scan archives, iChecker enabled, Heuristic analyzer enabled<br>**Logging:** Enabled |
| **Process Control** | Configured based on auto-profiling — allows only known-good processes |
| **Network Control** | Configured based on auto-profiling — ingress/egress rules per CIDR and port |
| **File System Monitoring** | Monitored sensitive paths: `/etc/*`, `/var/*` |

---

## Quick Reference Table

| Component                  | Status | Notes                                                             |
| -------------------------- | ------ | ----------------------------------------------------------------- |
| CI/CD Pipeline Integration | ✅ Done | GitLab CI with KCS scanner                                        |
| Registry Integration       | ✅ Done | Connected to container registry                                   |
| K8s Namespace & KCS Scope  | ✅ Done | Namespace + Scope + RBAC                                          |
| Scanner Policy             | ✅ Done | All scan types enabled                                            |
| Assurance Policy           | ✅ Done | Fail on critical vulns, malware, config errors, secrets           |
| Runtime Policy             | ✅ Done | Enforce mode, excluded: `postgres:*`, `redis:*`, `*:alpin-16`     |
| Cosign Integration         | ✅ Done | Image signature verification                                      |
| Runtime Profile            | ✅ Done | File Threat Protection, Process Ctrl, Network Ctrl, FS Monitoring |

---

## Issues

| Issue | Description | Status |
|-------|-------------|--------|
| Image Signature Verification | Cosign integration is configured but signature verification fails with error: *"cosign public key is not found"* — unknown error. The public key appears to not be reachable/valid by KCS. | 🔴 Open — needs investigation |

## Inquiries

| Inquiry                                   | Details                                                                                                                                                                                                                                                                                         |
| ----------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Admission Controller Policy Customization | Runtime policies are not declarative/customizable beyond the built-in options. You can only configure the preset rules — cannot add new custom admission rules or create runtime policies to block vulnerable workloads **after** they have already been deployed (only blocks at pod startup). |
| File System Monitoring Mode               | Restricted to **Audit** mode only — this is a **KCS limitation**. Enforce mode is not available for File System Monitoring.                                                                                                                                                                     |
| KIRA AI                                   | Only analyze docker layers.                                                                                                                                                                                                                                                                     |

## Environment Demo

RDP to : uvo1kx0gba90zokeksk.vm.cld.sr

User: Administrator

Domain: DEMO.LAB

Password Ka5per5Ky!

This server is also the DNS kcs is accessible at <https://kcs.demo.lab> admin/Ka5per5Ky!

---
