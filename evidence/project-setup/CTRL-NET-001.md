# CTRL-NET-001 — secure remote Plane access preflight

Date: 2026-10-13 (Europe/Istanbul).
Result: BLOCKED_BY_NETWORK_CONFIGURATION — installation requires a further local administrator authentication; privileged firewall preflight succeeded. Tailscale is absent; no node login URL or share invitation exists. Remote access and least privilege are not certified.

## Purpose and authority

Provide only the ailab machine's Plane TCP8080 to three external teammates through individual Tailscale machine sharing. No whole-tailnet invitations, subnet routing, exit node, Tailscale SSH, Funnel, router forwarding or public Plane publication. This is host operations only; no product WP, Plane project data or GitHub operation is authorized.

## Observed preflight

- Host ailab; Ubuntu26.04.1 LTS/resolute; kernel7.0.0-38-generic; operator ailab(uid1000).
- LAN interface eno1:192.168.5.29/24. No Tailscale interface/IP.
- ListeningTCP:8080 and8443 onIPv4/IPv6 wildcard addresses; localhost DNS53 and printing631. Wildcard Plane binds existed before this task; no bind/public exposure was added. Router/public reachability is not established by this local inspection.
- plane-app-proxy-1 publishes host8080→container80 and8443→443. Other Plane services expose container ports only in the inspected Docker listing.
- Localhost http://127.0.0.1:8080/ andLAN http://192.168.5.29:8080/ bothHTTP200. HTML title identifies Plane.
- Compose:all12services running; web/admin/space reporthealthy; remaining containers do not expose a Docker healthcheck result in the inspected status.
- RustDesk service active; its configuration and session model untouched.
- Tailscale executable/package absent; tailscaled LoadState=not-found,ActiveState=inactive. Version/authentication/node/FQDN/connectivity/netcheck unavailable.
- UFW/nft tooling present. /etc/ufw/ufw.conf saysENABLED=no; privileged preflight confirmedUFW inactive andDocker nft DNAT8080→172.18.0.7:80/8443→443. Full public/router reachability remains unverified. Noninteractive sudo requires authentication. A legitimate sudo prompt was presented without requesting a chat password; then local graphical administrator authentication for read-only ufw/nft inspection was attempted. Graphical authentication succeeded for the read-only preflight; the subsequent officialinstallation request remained unauthenticated and was cancelled before handback. No firewall mutation or installation executed.

## Official installation selected, not executed

Official stable Ubuntu resolute packages exist. Verify administrator access locally and complete privileged preflight before installation. Use the official keyring/list and apt mechanism; install onlytailscale and required dependencies, never upgrade unrelated packages. A scoped apt update may target onlytailscale.list once added. No unofficial release/codename substitution.

Sources:
- https://pkgs.tailscale.com/stable/ (Ubuntu26.04/resolute)
- https://tailscale.com/docs/install/linux

After installation verifyversion/service. Use ordinary interactive sudo tailscale up/login with no keys or credentials in chat. Display its fresh browser URL only to the operator; never record it here. Do not advertise routes/exit nodes or enableSSH/Funnel. Continue only after node identity/IP is observed.

## Firewall and public exposure

No firewall/router/Docker network rule changed. No new public8080 exposure; pre-existing wildcard8080/8443 binds remain. No public-exposure guarantee is inferred from private LAN addresses. Do not add redundant8080 rules. If Tailscale reachesPlane, retainexisting firewall. If blocked, prove the exact blocker before a narrow interface-onlyTCP8080 change; preserveLAN/RustDesk. Docker port publications require consideration of the actual forwarding chain, not assumed UFW enforcement.

## Access policy and sharing — pending

No authenticated tailnet or readablepolicy exists on this host yet. No API token requested/created. Current owner policy is UNKNOWN; a default allow-all policy must not be assumed restrictive. Sharing alone does not prove port-level restriction.

Policy shape for owner review only, not applied: preserve legitimate existing direct-member/tag/service grants, replace any broad source rule effective for shared users, and grantautogroup:shared onlyTCP8080 to this exact node. Exact IP/alias binding is deferred until authentication; no IP is manufactured. Conceptual HuJSONfragment:

```json
{
  "grants": [
    {"src": ["autogroup:member"], "dst": ["*"], "ip": ["*"]},
    {"src": ["autogroup:shared"], "dst": ["ailab-plane"], "ip": ["tcp:8080"]}
  ]
}
```

This is NOT a ready-to-apply policy or full replacement. Defineailab-plane inhosts using the observed TailscaleIPv4/32 first. The direct-member grant is appropriate only if that matches the owner's existing intended access; preserve any separately authorized tagged/service policy. Grants/ACLs are additive:another broad matching rule would defeat the restriction. Check all effective grants/ACLs and policytests before sharing. ValidateTCP8080 allowed andSSH22/8443/arbitrary other ports denied from a real shared recipient; localself-connect alone is insufficient.

Official policy and sharing references:
- https://tailscale.com/docs/reference/targets-and-selectors
- https://tailscale.com/docs/reference/syntax/grants
- https://tailscale.com/docs/features/sharing

After restrictive policy approval/application:AdminConsole→Machines→observedailab node→Share→Share byemail; single-recipient invites toselmanozdemir430@gmail.com,batuhankaya0204@gmail.com,yavuzgumus@gmail.com. No whole-tailnet invite/public reusable sharelink. No machine-sharing operation executed.

## Plane URL/origin audit

Actual plane.env:APP_DOMAIN=192.168.5.29;WEB_URL=http://192.168.5.29:8080;CORS_ALLOWED_ORIGINS=http://192.168.5.29:8080. Inspectedsettings defaultALLOWED_HOSTS=* and deriveCSRF_TRUSTED_ORIGINS fromCORS origins. authentication/utils/host.py selectssettings.WEB_URL/APP_BASE_URL rather than the incominghost; configured-origin authentication/link behavior is a potential remote blocker. WithMinIO enabled,settings also derivesobject URLs fromWEB_URL. HomepageHTTP200 is not proof of remote login/callback/link correctness.

No application configuration or containerrestart performed. After the actualTailscale URL works, test login/redirect/generatedlinks without fabricating accounts. A change toWEB_URL/origins needs exact impact/restart review and LAN administration preservation; no change is justified before node reachability. If uncertain useHUMAN_APPROVAL_REQUIRED:PLANE_BASE_URL_CHANGE.

## Validation and next human gate

ServerLAN/localhealth PASS; repositorydiff hygiene PASS. Remote Plane reachability, Tailscale auth/IP/service, effective port policy and acceptedshares NOT VERIFIED. RustDeskremainsactive; allPlanecontainersrunning. No code change or projectctl test rerun is needed for this evidence-only preflight.

First required action:local administrator authentication for the already authorized officialinstallation; then interactive ownerTailscale login. Policyconsole review/application and individual machine-share acceptance remain later gates. No auth/shareURLs,keys,cookies,tokens or passwords appear in this evidence.

FILES CHANGED:This uncommitted evidenceonly. Canonicaldocs/ andAGENTS.md unchanged. No commit/push/PR change.
PLANE PROJECT MUTATIONS:NONE
GITHUB MUTATIONS:NONE
WP ASSIGNMENTS:NONE

Handback: pending installation authentication was closed; no background installation is intentionally left running. Authentication and installation must be resumed locally. No Tailscale repository/keyring/package was added.

## Final independent continuation — 2026-10-13

Current status: **SERVER_SIDE_TRANSPORT_VERIFIED_CANONICAL_URL_DECISION_PENDING**. This supersedes the historical absent-installation blocker above without erasing it. No TAILSCALE_ACCESS_READY or end-to-end login guarantee is claimed. The latest human request authorizes this evidence checkpoint and updating the unreviewed setup PR; the original preflight's no-GitHub authorization applies only to that historical run.

### Fresh network observations

- Human installed/authenticated Tailscale after the historical legitimate administrator-authentication blocker. Version1.104.1, commit7f4efe814ff14b064eb080344389ceb9ea2d37ac; tailscaled active, BackendStateRunning, nodeailab online.
- IPv4:100.96.181.5. MagicDNS:ailab.taila966e9.ts.net resolves locally to that address. LAN, TailscaleIPv4 and MagicDNS homepage eachHTTP200.
- RunSSHfalse; advertised routesnull; exit-node ID/IPempty and Self.ExitNode/ExitNodeOptionfalse. Serve and Funnel both reportNo serve config. Capabilities permitting a feature do not mean it is enabled. No feature/network/router/firewall setting changed by this pass.
- All12 Plane containers running; web/admin/space reporthealthy. Remaining services have no Docker healthcheck status; live-service /live/health returnsHTTP200 overLAN and Tailscale. Existing wildcardTCP8080/8443 binds remain unchanged; no public reachability certification. RustDesk configuration untouched.
- Firewall: /etc/ufw/ufw.conf remainsENABLED=no; systemctl reportsufw active (service state alone is not active-rule proof). Fresh privilegedUFW/nft readback is unavailable: noninteractive sudo needs local authentication and nft denies non-root inspection. Earlier privilegedUFWinactive/DockerDNAT observation is historical; current kernel rules are not re-certified. No authentication request or firewall change made.

### Access policy: human-attested, not independently fetched

The human reports member→all normal access and shared→100.96.181.5 port8080. No supported policy-console/API read credential was supplied; no new token or policy mutation attempted. The attested grant usesip:["8080"]. Official grants syntax says a bare port impliesTCP,UDP andICMP access; it is **not a TCP-only grant**. ExactTCP-only syntax istcp:8080, but this pass does not overwrite the human-applied policy. Full additive policy restrictions remain unverified. Source:https://tailscale.com/docs/reference/syntax/grants (network-layer capabilities).

Machine sharing: NOT_VERIFIED by this host audit. Real accepted shared teammate transport/login and deniedSSH22/8443/other-port checks: NOT_EXECUTED. Local self-connect and the observed own-tailnet peer do not prove shared-recipient access. No auth/shareURL, cookie, token, API key or credential is recorded here.

### Installed Plane configuration contract and decision

Installed instance: Plane Community1.4.2; backendmakeplane/plane-backend:stable, imageIDsha256:90032ce088708889b60c00d491897916f4deb882facda27db59fd10fb68729ef. Authority is the actual installed source, not another version's documentation.

Original and final non-secret configuration remain:

- APP_DOMAIN=192.168.5.29
- WEB_URL=http://192.168.5.29:8080
- CORS_ALLOWED_ORIGINS=http://192.168.5.29:8080

Installed /code/plane/settings/common.py comma-splitsCORS_ALLOWED_ORIGINS and setsCSRF_TRUSTED_ORIGINS to the same list; ALLOWED_HOSTS defaults*. HTTP origins implynonsecureCSRFcookies. Multiple trusted origins are supported. Both installed authentication/utils/host.py andutils/host.py selectconfiguredWEB_URL/APP_BASE_URL, not the incoming hostname, with optional app/admin/space base overrides. App email-auth handlers use this for redirects; the UI invitation handler passes the samebase_host to the invitation task. MinIO artifact-domain/protocol generation derives fromWEB_URL. Exact future generated links cannot be tested without creating/authenticating a real session; none were created.

Live-serviceapps/live/dist/start.mjs also comma-splitsCORS_ALLOWED_ORIGINS; its HTTP health route works, but no credentialed websocket session/upgrade is certified. BackendLIVE_BASE_URL is optional; missing value does not prove a credentialed client session works through alternate origins. Same-origin public /api/instances/ returns200 on all three URLs; onlyLAN emitsAccess-Control-Allow-Origin for matchingOrigin. /auth/sign-in/ GET returns405 at all origins (installed endpoint is not a GET login success test). No POST or credentials were used.

**HUMAN_DECISION_REQUIRED: PLANE_CANONICAL_WEB_URL**

A single canonicalTailscale/MagicDNS URL changes authentication/link/artifact targets for LAN clients that may lackTailscale. A sole trusted-origin addition does not repair canonical remote redirects. No safe complete dual-origin authentication configuration is proven. Under the explicit decision policy, configuration is left unchanged. The owner must choose the canonical access URL/client requirements or an approved dual-origin solution; currentMagicDNS availability alone does not establish LAN-only client compatibility.

Services restarted:NONE. Config backup:NONE needed. Database migration:NONE. Rollback:NONE needed. Project/API adapter/user data untouched. Existing12containers remain running;HTTP200 is transport proof only.

### Repository / external verification

Setup branchsetup/project-management-bootstrap; preflightHEAD69ade2236900bcc94b38e1e197765c499a5752b2. Full existing suite:146passed in63.12s. projectctlvalidate:PASS,947preserved warnings,execution_statusUNAVAILABLE(documentation only). Canonicaldocs/ andAGENTS.md unchanged frommain. gitdiff--checkPASS; localPlanecredential file remains ignored. This evidence is the only setup-file change in this control.

Fresh final read-onlyPlanev1 audit usesX-API-Key loaded literally without printing it, includingTailscale API reachability: Graduation Project/CAP,179unique canonicalWPs,allBACKLOG,73assigned/106unassigned,29modules,13cycles,10labels(BLOCKED+M0–M8),canonical8states+CANCELED. Oneproject/workspace member; the three previously createdPlaneinvitations remainunaccepted. No assignable teammate identity is inferred. No Plane project mutation, WP assignment or dummy user creation.

GitHubpreflightPR#2OPEN/unmerged,noreviews,head69ade22CIgreen. Fresh collaborator readback nowshowsYavuzgmusacceptedwrite;selorito/eilonninvitationsstillpending. This does not activatePlane membership. Latest-request-authorized evidence commit/push/PR-body update and actual resulting CI are reported after execution; no approval/merge is authorized.

Existing privatebackupplane-20261012T001234Z-e6315559:all40manifestchecksums match;manifestSHA2567782a9531168c3bf826139a8ca203e1b4da5c8aba208fe849e6252f89c559468. Existing isolatedPostgreSQLrestore-verification.jsonPASS remains,networknone,no livevolumes or live restore. Fullobject-store/application restore is not certified; no extra backup/restore performed.

Next gates:canonicalURL decision; owner machine-sharing/policy verification and real teammate transport/login/deny-port validation; genuine independent current-head GitHubreview and individualPlaneacceptance. Product implementation, automatic READY/DONE, merge and reconciliation push remain out of scope.

PLANE MUTATIONS:NONE
HOST CONFIGURATION MUTATIONS:NONE
WP ASSIGNMENTS:NONE
GIT MERGE:NONE
