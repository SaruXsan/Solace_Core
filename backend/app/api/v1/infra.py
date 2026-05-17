"""Infrastructure and AppSec evidence list endpoints (foundation placeholders)."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_configured_db, require_permission
from app.models import infra as infra_models
from app.models.platform import CoreUser

router = APIRouter(prefix="/evidence", tags=["evidence"])


def _list_table(db: Session, model, fields: list[str]) -> list[dict]:
    rows = db.scalars(select(model).limit(200)).all()
    out = []
    for r in rows:
        row = {}
        for f in fields:
            val = getattr(r, f)
            if f == "id" or f.endswith("_id"):
                row[f] = str(val) if val is not None else None
            else:
                row[f] = val
        out.append(row)
    return out


@router.get("/infra/applications")
def infra_apps(db: Session = Depends(get_configured_db), _u: CoreUser = Depends(require_permission("compliance.read"))):
    return _list_table(db, infra_models.InfraApplication, ["id", "name", "owner"])


@router.get("/infra/environments")
def infra_envs(db: Session = Depends(get_configured_db), _u: CoreUser = Depends(require_permission("compliance.read"))):
    return _list_table(db, infra_models.InfraEnvironment, ["id", "name", "environment_type"])


@router.get("/infra/servers")
def infra_servers(db: Session = Depends(get_configured_db), _u: CoreUser = Depends(require_permission("compliance.read"))):
    return _list_table(db, infra_models.InfraServer, ["id", "hostname"])


@router.get("/infra/network-zones")
def infra_zones(db: Session = Depends(get_configured_db), _u: CoreUser = Depends(require_permission("compliance.read"))):
    return _list_table(db, infra_models.InfraNetworkZone, ["id", "name", "zone_type"])


@router.get("/infra/open-ports")
def infra_ports(db: Session = Depends(get_configured_db), _u: CoreUser = Depends(require_permission("compliance.read"))):
    return _list_table(db, infra_models.InfraOpenPort, ["id", "port", "protocol"])


@router.get("/infra/certificates")
def infra_certs(db: Session = Depends(get_configured_db), _u: CoreUser = Depends(require_permission("compliance.read"))):
    return _list_table(db, infra_models.InfraCertificate, ["id", "common_name"])


@router.get("/infra/firewall-rules")
def infra_fw(db: Session = Depends(get_configured_db), _u: CoreUser = Depends(require_permission("compliance.read"))):
    return _list_table(db, infra_models.InfraFirewallRule, ["id", "rule_name", "action"])


@router.get("/infra/patch-records")
def infra_patches(db: Session = Depends(get_configured_db), _u: CoreUser = Depends(require_permission("compliance.read"))):
    return _list_table(db, infra_models.InfraPatchRecord, ["id", "target", "patch_id"])


@router.get("/infra/hardening-checks")
def infra_hardening(db: Session = Depends(get_configured_db), _u: CoreUser = Depends(require_permission("compliance.read"))):
    return _list_table(db, infra_models.InfraHardeningCheck, ["id", "check_name", "passed"])


@router.get("/infra/remote-access")
def infra_remote(db: Session = Depends(get_configured_db), _u: CoreUser = Depends(require_permission("compliance.read"))):
    return _list_table(db, infra_models.InfraRemoteAccessRule, ["id", "rule_name"])


@router.get("/infra/backups")
def infra_backups(db: Session = Depends(get_configured_db), _u: CoreUser = Depends(require_permission("compliance.read"))):
    return _list_table(db, infra_models.InfraBackupRecord, ["id", "system_name"])


@router.get("/infra/security-tools")
def infra_tools(db: Session = Depends(get_configured_db), _u: CoreUser = Depends(require_permission("compliance.read"))):
    return _list_table(db, infra_models.InfraSecurityTool, ["id", "tool_name", "vendor"])


@router.get("/appsec/ssdlc")
def appsec_ssdlc(db: Session = Depends(get_configured_db), _u: CoreUser = Depends(require_permission("compliance.read"))):
    return _list_table(db, infra_models.AppSecSSDLCRecord, ["id", "project_name", "phase"])


@router.get("/appsec/code-reviews")
def appsec_reviews(db: Session = Depends(get_configured_db), _u: CoreUser = Depends(require_permission("compliance.read"))):
    return _list_table(db, infra_models.AppSecCodeReview, ["id", "repository", "status"])


@router.get("/appsec/sast")
def appsec_sast(db: Session = Depends(get_configured_db), _u: CoreUser = Depends(require_permission("compliance.read"))):
    return _list_table(db, infra_models.AppSecSASTScan, ["id", "tool", "findings_count"])


@router.get("/appsec/dast")
def appsec_dast(db: Session = Depends(get_configured_db), _u: CoreUser = Depends(require_permission("compliance.read"))):
    return _list_table(db, infra_models.AppSecDASTScan, ["id", "target_url", "findings_count"])


@router.get("/appsec/pen-tests")
def appsec_pentest(db: Session = Depends(get_configured_db), _u: CoreUser = Depends(require_permission("compliance.read"))):
    return _list_table(db, infra_models.AppSecPenTest, ["id", "scope", "status"])


@router.get("/appsec/dependency-scans")
def appsec_deps(db: Session = Depends(get_configured_db), _u: CoreUser = Depends(require_permission("compliance.read"))):
    return _list_table(db, infra_models.AppSecDependencyScan, ["id", "project", "critical_count"])


@router.get("/appsec/security-headers")
def appsec_headers(db: Session = Depends(get_configured_db), _u: CoreUser = Depends(require_permission("compliance.read"))):
    return _list_table(db, infra_models.AppSecSecurityHeader, ["id", "endpoint", "compliant"])


@router.get("/appsec/api-controls")
def appsec_api(db: Session = Depends(get_configured_db), _u: CoreUser = Depends(require_permission("compliance.read"))):
    return _list_table(db, infra_models.AppSecAPIControl, ["id", "api_name", "auth_required"])


@router.get("/appsec/vulnerabilities")
def appsec_vulns(db: Session = Depends(get_configured_db), _u: CoreUser = Depends(require_permission("compliance.read"))):
    return _list_table(db, infra_models.AppSecVulnerability, ["id", "cve_id", "severity", "status"])


@router.get("/appsec/remediation")
def appsec_remediation(db: Session = Depends(get_configured_db), _u: CoreUser = Depends(require_permission("compliance.read"))):
    return _list_table(db, infra_models.AppSecRemediationAction, ["id", "action"])
