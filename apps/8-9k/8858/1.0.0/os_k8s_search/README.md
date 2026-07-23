# os_k8s_search

A Splunk app that exposes the Kubernetes API as SPL search commands.
Operators write `| k8s kind=pods` instead of `kubectl get pods` — no
ingestion, no indexing, just live API calls at search time.

See https://www.outcoldsolutions.com for product information.

## Security model

The app talks to your Kubernetes API servers with credentials you
configure on the setup page. This section is for the SecOps reviewer
deciding whether that is safe in a multi-tenant Splunk deployment.

### Roles and capabilities

Two custom roles ship in `authorize.conf`:

- **`role_k8s_search_user`** (base) grants `run_k8s_search` — the
  runtime gate for `| k8s` / `| k8slogs` / `| k8sevents` /
  `| k8sdescribe` and for managing one's *own* per-user credentials. A
  user who can authenticate to Splunk but does not hold this role
  cannot run the commands. The base role deliberately does **not**
  carry `list_storage_passwords`; the search command resolves the
  credentials it needs through an internal system-context handler that
  enforces a per-user entitlement check, so no search user can read the
  raw credential store.
- **`role_k8s_search_admin`** (Kubernetes administrator) adds
  `edit_k8s_search_clusters` — create/update/delete cluster definitions
  and import kubeconfigs. Grant it to your platform team; it does not
  require full Splunk admin. (Splunk's built-in `admin_all_objects` is
  accepted as a fallback so a fresh admin can configure the app before
  roles are assigned.)

### Credential modes and what isolates whom

A cluster can authenticate in one of three ways. Pick per cluster based
on how sensitive that cluster is:

| Mode | How it authenticates | Isolation between Splunk users |
| --- | --- | --- |
| **Shared default credential** | One token/cert stored for the cluster; every search uses it | **None.** Every user who can query the cluster gets the credential's full RBAC. |
| **Per-user credential** | Each user pastes their own token on the setup page (`kubeauth`) | **Per user.** A token is stored in its owner's namespace and resolved only there, so a user can read only their own — never another user's. |
| **Impersonation** | A server-side service account with the `impersonate` RBAC verb; each request stamps `Impersonate-User: <splunk user>` | **Per user, enforced by the Kubernetes API server.** The bearer never leaves the server; the API server applies RBAC as the requesting Splunk user. |

**Threat-model boundary you must understand (shared mode):** the shared
default credential of a non-impersonation cluster is *resolvable in
clear text* by any user who can run searches against it. That is by
design — they already authenticate to Kubernetes with it on every
search — but it means such a user can extract the token and use it
**outside Splunk** (e.g. with `kubectl`), with that credential's full
RBAC, **outside the Splunk audit trail**, until you rotate it.

Therefore: **for any cluster whose service account can see sensitive
data, use per-user credentials or impersonation, not a shared
credential.** Shared mode is appropriate for a low-privilege,
read-only "everyone sees the same view" service account. Treat a shared
service-account token as a long-lived secret: scope its RBAC to the
minimum the dashboards need, and rotate it on a schedule.

### Impersonation: required RBAC (read this before enabling it)

Impersonation is the strongest isolation mode and is the recommended
choice for multi-tenant clusters, but the service account you bind is
powerful — it can act as other identities — so grant it narrowly:

- **Grant `impersonate` on `users` ONLY. Never grant `impersonate` on
  `groups`.** A holder of open group-impersonation can impersonate
  `system:masters` and become an unrevocable cluster-admin. The app
  only ever stamps `Impersonate-User`, so the `users` verb is all it
  needs.
- **Bind your Kubernetes RBAC to the impersonated *usernames*, not to
  groups.** The app stamps the user but not the user's groups, so a
  `RoleBinding`/`ClusterRoleBinding` that grants access via a *group*
  will not apply to an impersonated request — the impersonated identity
  carries only `system:authenticated`. This fails safe (a user sees too
  little, never too much), but it means group-based RBAC silently
  grants nothing through this app.
- Scheduled saved searches that run as `nobody` are refused
  impersonation (they have no real user identity); own such searches
  as a real user.

Minimal service-account RBAC for impersonation mode:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: k8s-search-impersonator
rules:
  - apiGroups: [""]
    resources: ["users"]      # users only — never "groups"
    verbs: ["impersonate"]
---
# Then grant the *impersonated users* their own read-only RBAC, e.g.
# bind the built-in "view" ClusterRole to each Splunk username:
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: k8s-search-view-alice
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: view
subjects:
  - kind: User
    name: alice            # the Splunk username, stamped as Impersonate-User
    apiGroup: rbac.authorization.k8s.io
```

### Per-user credentials and your username

There is no username-character restriction. A per-user credential is
stored under a name that includes a SHA-256 hash of your Splunk
username, so two users who configure the *same* cluster never collide.
Your username is hashed, not stored verbatim and not character-checked,
so any username (including unusual LDAP/SAML principals containing `__`)
works the same way. When a search resolves a per-user credential, the
handler requires the hash embedded in the reference to match the hash of
the authenticated user making the request — so one user can never
resolve another's token, regardless of how either name is spelled, even
though the hash itself is not secret.

### No telemetry

The app makes no outbound calls other than to the Kubernetes API
servers you configure and to the local `splunkd`. It does not phone
home, and it ships no analytics or license-check beacon — safe for
air-gapped installs.

## Cache tuning

The search commands cache LIST / GET results on disk under
`$SPLUNK_HOME/var/run/os_k8s_search/cache/` by default. Conservative
TTLs (30 seconds for LIST, 10 seconds for GET) deduplicate the
burst of panel-search requests a dashboard load fires without
making staleness operator-visible.

**Per-search override** with the `cache=` SPL parameter:

```spl
| k8s kind=pods cache=2m        # cache this LIST for 2 minutes —
                                # appropriate for heavy fleet panels
| k8s kind=pods cache=0         # force-live; bypass cache entirely
| k8s kind=pods                 # inherit the per-stanza default
```

**Per-install** in `local/k8s_search.conf [cache]`:

```ini
[cache]
# master kill switch
enabled = true
# kubectl-style schema cache
discovery_ttl = 10m
# default for `| k8s` and `| k8sevents`
list_default_ttl = 30s
# default for `| k8sdescribe`
get_default_ttl = 10s
```

**Diagnostic SPL** — records from `| k8s`, `| k8sdescribe`, and
`| k8sevents` carry `_cache_hit` and `_cache_age_seconds`, so you can see at a glance whether
the cache is the cause of stale-looking output:

```spl
| k8s kind=pods
| stats count by _cache_hit
```

For multi-cluster fan-out, join with the existing `cluster`
field to see per-cluster hit rates:

```spl
| k8s kind=pods context=*
| stats count by cluster _cache_hit
```

### When to opt out

- **Alert / incident searches** should set `cache=0` so on-call
  sees live data. The bundled dashboards do not pin this —
  they inherit the conservative 30s / 10s defaults, which are
  invisible against Splunk's typical 60s dashboard refresh
  cadence. If you have a search where 30s staleness genuinely
  matters (paging alerts, real-time incident tiles), add
  `cache=0` at the search.
- **`kind=secrets` automatically bypasses the cache** — Secret
  payloads never land on disk regardless of the configured TTL.
  Explicit `cache=<positive>` on a Secrets search errors with
  a clear message.

### SHC behavior

Each search head member has its own local cache under
`var/run/` — this directory is not part of the SHC replication
channel. Panels from a single dashboard load that all dispatch
to the same SH member share a warm cache; panels that dispatch
across members hit a colder cache on each member's first
encounter with the request. Sticky-session affinity on the SHC
load balancer improves the hit rate.

The setup page's **Clear cache** button (and the underlying
`DELETE /k8s_search/cache` endpoint) runs on whichever member
received the REST call — it does NOT fan out to other SHC
members. Each member's cache is bounded by its per-search TTL
ceiling (default 30s LIST / 10s GET) and trimmed every 5
minutes by the per-member sweeper, so a one-time clear on a
single member is rarely the wrong answer. When you need every
member's cache flushed immediately (e.g. after rotating a
credential and you don't want to wait out the TTL on the other
members), trigger the button on each member individually, or
restart the SHC members so each one rebuilds from cold.

### Splunk Cloud Victoria

If a Cloud install rejects writes to `$SPLUNK_HOME/var/run/`,
the cache layer's automatic disk-error fallback detects the
failure on first use and runs uncached for the rest of the
process lifetime (logged WARN once). Operators can also flip
`[cache] enabled = false` explicitly via the setup page's
Disable cache toggle.

<!-- BINARY-HASHES:START -->
## Binary File Declaration

AppInspect requires every shipped binary to be declared with
its SHA512 hash. Splunk verifies these match the bytes on disk
at install time.

- `bin/platform/darwin_amd64/k8s_search`
    - Source: github.com/outcoldsolutions (proprietary)
    - SHA512: `3d988aea36192d1ee211a7f9a70bfc6e9649844a502065f0dc6f16d27ddd04fdbec22769672669474a637b21fbfb4d1963d71cb7fe64c5eb2722aa8a1a76ae65`
- `bin/platform/darwin_arm64/k8s_search`
    - Source: github.com/outcoldsolutions (proprietary)
    - SHA512: `5ba991178e955f6c25af4a03506685e835eaa67e56d0a364bc8db418ca74844dcfe75f0bf1eab623f7444a9a6056b0e1e41299d4606cf46ffc09e7647b2d3664`
- `bin/platform/linux_amd64/k8s_search`
    - Source: github.com/outcoldsolutions (proprietary)
    - SHA512: `ed22f95a651f4f204226001d5df47a7d7b796798a2efc6a84c3a9fe82c3414d8252e7b863648b5cbc9dd06ba090ba6e6052496f4910bb7a50baddebfc07edd7b`
- `bin/platform/linux_arm64/k8s_search`
    - Source: github.com/outcoldsolutions (proprietary)
    - SHA512: `921b6f0b6453c719dc78fe9630cfa0dc4a2a45b7d5e284fa2ea63ad15aa1f6741f98ab704aa9926a007ff1043153eaf85ec6d28b29c937007c14ee9ed26d02c5`
- `bin/platform/windows_amd64/k8s_search.exe`
    - Source: github.com/outcoldsolutions (proprietary)
    - SHA512: `45acd81c9da0ba783c64cf5ebaf98b863b02a5c266947ce7b94a34907bebf4e8d1589209be17263687c9ef55029d85787060ba8ff696193cacfc84052825e11f`
<!-- BINARY-HASHES:END -->
