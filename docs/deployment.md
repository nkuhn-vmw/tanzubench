# Deployment — Cloud Foundry

The TanzuBench webapp is deployed to a Cloud Foundry
foundation as a static app using the `staticfile_buildpack`.

## One-Time Setup

### 1. Discover the CF system domain

Use your OpsManager credentials file to find the system domain:

```bash
export OM_ENV=<path-to-your-om-cli.yml>
eval "$(om -e $OM_ENV bosh-env 2>/dev/null)"
bosh -d cf manifest 2>/dev/null | grep -i "system_domain" | head -3
```

Record the domain (e.g., `sys.<foundation>.example.com`).

### 2. Create the org and space

```bash
cf api "https://api.<system-domain>" --skip-ssl-validation
cf auth admin <admin-password>   # from your OpsManager credentials
cf create-org tanzubench
cf create-space tanzubench -o tanzubench
```

### 3. Create a dedicated deploy user

```bash
cf create-user tanzubench-deploy "$(openssl rand -hex 16)"
# Record the generated password — you will need it for GitHub secrets.
cf set-space-role tanzubench-deploy tanzubench tanzubench SpaceDeveloper
```

### 4. Add GitHub repo secrets

In the GitHub repo settings, add:

- `CF_API` — `https://api.<system-domain>`
- `CF_USER` — `tanzubench-deploy`
- `CF_PASSWORD` — the password generated in step 3
- `CF_ORG` — `tanzubench`
- `CF_SPACE` — `tanzubench`

### 5. First manual deploy

```bash
cd web
npm ci && npm run build
cf target -o tanzubench -s tanzubench
cf push -f manifest.yml
```

### 6. Add a custom route (optional)

```bash
cf map-route tanzubench <apps-domain> --hostname tanzubench
```

## Ongoing Operations

- Merges to `main` auto-deploy via `.github/workflows/deploy.yml`.
- Rollback: `cf rollback tanzubench` restores the previous droplet.
- View logs: `cf logs tanzubench --recent`
