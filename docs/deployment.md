# 🚀 Deployment & CI/CD Pipeline

Clew supports local execution, Kubernetes deployment via Helm, and automated documentation publishing to GitHub Pages.

---

## 1. Local Documentation Server

To run the MkDocs server locally with hot reloading:

```powershell
./scripts/serve_docs.ps1
```

The documentation server will launch at `http://127.0.0.1:8000`.

---

## 2. GitHub Pages CI/CD Pipeline

Clew includes an automated GitHub Actions pipeline (`.github/workflows/deploy-docs.yml`) that builds and deploys documentation to GitHub Pages whenever changes are pushed to `main` or `v2`.

### GitHub Repository Setup

1. **Configure Workflow Permissions**:
   - Go to your repository on GitHub (`https://github.com/YOUR_USERNAME/clew`).
   - Navigate to **Settings** -> **Actions** -> **General**.
   - Scroll down to **Workflow permissions**, select **Read and write permissions**, and click **Save**.

2. **Configure GitHub Pages**:
   - Navigate to **Settings** -> **Pages**.
   - Under **Build and deployment** -> **Source**, select **Deploy from a branch**.
   - Under **Branch**, select `gh-pages` and `/ (root)` as the folder, then click **Save**.

3. **Trigger Workflow**:
   ```bash
   git add .github/workflows/deploy-docs.yml mkdocs.yml docs/ scripts/serve_docs.ps1
   git commit -m "ci: add GitHub Actions workflow for automatic MkDocs deployment"
   git push origin v2
   ```

---

## 3. Kubernetes Helm Deployment

Clew includes production-ready Helm manifests located in `helm/`:
- Multi-pod deployment for Streamlit (`clew-ui`), FastAPI (`clew-mobile-ui`), and LiveKit Voice (`clew-agent`).
- PostgreSQL StatefulSet with `pgvector` extension support.
- Single-node pod affinity rules to maintain SQLite WAL concurrency safety when operating in V1 mode.
