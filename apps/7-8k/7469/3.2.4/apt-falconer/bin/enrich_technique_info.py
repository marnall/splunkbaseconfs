from __future__ import annotations

import csv
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TECHNIQUES_DIR = ROOT / "appserver" / "static" / "data" / "techniques"
MITRE_CSV = ROOT / "lookups" / "mitre_techniques.csv"

MANUAL_DESCRIPTIONS = {
    "T1557.004": "Adversaries may stand up a rogue wireless access point that imitates a trusted network to lure victim devices into associating with it.<br/>Once traffic is flowing through the attacker-controlled access point, they can observe credentials, capture session material, manipulate responses, or stage follow-on collection against the victim.",
    "T1213.004": "Adversaries may mine customer relationship management platforms for account notes, contact records, case details, and business process context.<br/>Access to CRM data can expose high-value targets, operational relationships, and sensitive customer information that supports phishing, fraud, or follow-on access operations.",
    "T1213.005": "Adversaries may collect information from enterprise messaging platforms such as Teams, Slack, or similar collaboration tools.<br/>Conversation history, shared files, channels, and direct messages can reveal credentials, incident chatter, internal plans, and opportunities for impersonation or lateral movement.",
    "T1213.006": "Adversaries may query databases to collect structured records, credentials, configuration data, or business-sensitive information.<br/>Database access can provide both immediate intelligence value and a path to broader compromise when application, customer, or identity data is stored centrally.",
    "T1680": "Adversaries may enumerate local disks, mounted volumes, and attached storage to understand where useful data resides and how much space is available.<br/>Drive discovery can inform staging decisions, identify backup or removable media, and help prioritize collection, encryption, or destruction actions.",
    "T1518.002": "Adversaries may inventory backup software and recovery tooling installed in the environment.<br/>Understanding what backup controls exist helps an operator decide how to evade restoration, identify high-value management systems, or target backup infrastructure before impact activity.",
    "T1059.011": "Adversaries may use the Lua scripting language to execute malicious logic inside applications, embedded runtimes, or extensible platforms that support Lua.<br/>Lua-based execution can blend with legitimate automation or application customization and may avoid controls tuned primarily for more common interpreters.",
    "T1059.012": "Adversaries may abuse hypervisor command-line interfaces to run administrative actions directly against virtualization infrastructure.<br/>This can enable execution, guest control, or environment manipulation from the management plane without relying on traditional in-guest tooling.",
    "T1059.013": "Adversaries may use container platform CLIs or APIs to execute commands inside containers or orchestrated workloads.<br/>This can provide a direct route to runtime access, post-exploitation automation, and control over workloads that may not be visible through standard endpoint-focused detections.",
    "T1675": "Adversaries may use native ESXi administration commands to run actions on a hypervisor or influence the workloads it manages.<br/>Because these commands are part of expected virtualization administration, malicious usage may blend with routine operations unless closely monitored.",
    "T1674": "Adversaries may generate synthetic input such as keystrokes or mouse actions to drive a victim system indirectly.<br/>Input injection can execute attacker intent in the context of an interactive session, bypassing some restrictions that apply to direct process creation or remote command execution.",
    "T1677": "Adversaries may poison CI/CD pipelines by inserting malicious logic into build definitions, runners, dependencies, or release workflows.<br/>Compromise at the pipeline layer can turn trusted automation into a distribution point for persistence, credential theft, or downstream software supply chain access.",
    "T1569.003": "Adversaries may invoke `systemctl` to start services, run units, or alter service state on Linux systems that use systemd.<br/>Abuse of service management can provide execution, persistence, or privilege leverage while appearing similar to legitimate administrative activity.",
    "T1204.005": "Adversaries may rely on a victim installing or loading a malicious library that appears legitimate or useful.<br/>Once introduced into the environment, that library can execute attacker-controlled code inside a trusted application or software distribution path.",
    "T1669": "Adversaries may obtain initial access by connecting to or abusing wireless networks used by the target environment.<br/>Weak wireless controls, exposed credentials, or proximity-based access can provide an entry path that bypasses some internet-facing defenses.",
    "T1505.006": "Adversaries may use malicious vSphere Installation Bundles to implant persistence directly on ESXi hosts.<br/>Because VIBs extend hypervisor functionality at a privileged layer, abuse can survive guest-level remediation and provide durable control over virtual infrastructure.",
    "T1546.017": "Adversaries may create or modify udev rules so that device-related events trigger attacker-controlled commands or scripts.<br/>This allows execution to occur automatically when hardware state changes, removable media appears, or other monitored conditions are met.",
    "T1546.018": "Adversaries may leverage Python startup behavior so malicious code runs automatically when Python launches in targeted contexts.<br/>Abuse of initialization hooks or startup files can provide quiet persistence inside developer tooling, automation, or application runtimes that depend on Python.",
    "T1668": "Adversaries may establish exclusive control over a compromised device or service so only their infrastructure can interact with it reliably.<br/>This can reduce competition from other operators, block defenders from normal access paths, and preserve a more stable persistence channel.",
    "T1176.001": "Adversaries may deploy malicious browser extensions to gain persistent access to user browsing activity, session material, or web application workflows.<br/>Because extensions operate inside the browser context, they can capture content and credentials from cloud services that traditional endpoint telemetry may miss.",
    "T1176.002": "Adversaries may abuse IDE extensions to persist inside developer workstations and software build environments.<br/>A malicious extension can inherit trusted access to source code, credentials, terminals, and project workflows, making it valuable for both persistence and collection.",
    "T1671": "Adversaries may abuse cloud application integrations and consented app-to-app trust to maintain long-term access in SaaS or identity environments.<br/>These integrations can retain access to data and administrative actions even after a user password change if the granted application permissions remain in place.",
    "T1204.004": "An adversary may rely on a user copying and pasting attacker-supplied commands or code into a trusted interpreter or administration tool.<br/>This technique is effective because the action appears user initiated and often leverages normal instructions, scripts, or troubleshooting guidance as the lure.",
    "T1002": "An adversary may compress data before exfiltration to reduce transfer size, stage material for movement, or package files into a more portable archive.<br/>Compression can also help blend outbound activity with common administrative utilities and prepare data for encryption or chunked transfer.",
    "T1022": "Adversaries may encrypt data before exfiltration so content is less visible to defenders inspecting outbound traffic or staged archives.<br/>Encrypting the payload separately from the transfer channel can make stolen data harder to inspect even when the transport itself is identified.",
    "T1098.007": "An adversary may add extra local or domain group memberships to an account they control in order to retain access or expand privileges over time.<br/>Group changes can silently grant broader access to systems, administrative tools, and protected resources without creating a brand-new account.",
    "T1681": "Threat actors may search public or private threat intelligence reporting about their own infrastructure, tooling, or campaigns.<br/>This helps them understand what defenders have already exposed, which indicators are burned, and how they may need to adapt future operations.",
}


def normalize_attack_id(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip().upper()
    if not value.startswith("T"):
        return None
    return value


def extract_attack_id(technique: dict) -> str | None:
    title = (technique.get("title") or "").strip()
    match = re.match(r"^(T\d{4}(?:\.\d{3})?):", title)
    return match.group(1) if match else None


def strip_citations(text: str) -> str:
    text = re.sub(r"\(Citation:[^)]+\)", "", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()


def markdown_links_to_text(text: str) -> str:
    return re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1", text)


def description_to_html(text: str) -> str:
    text = markdown_links_to_text(strip_citations(text))
    text = re.sub(r"\n+", "<br/>", text)
    text = re.sub(r"(?<!<br/>)(?<=\.)\s+(?=[A-Z])", "<br/>", text)
    return text.strip()


def metadata_to_html(label: str, value: str) -> str:
    value = (value or "").strip()
    if not value:
        return ""
    return f"<strong>{label}:</strong> {value}"


def is_generic_info_html(text: str | None) -> bool:
    text = (text or "").strip()
    if not text or "<br/>" in text or text.startswith("Duplicate entry"):
        return False
    return True


def load_descriptions() -> dict[str, str]:
    descriptions: dict[str, str] = {}
    with MITRE_CSV.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            attack_id = normalize_attack_id(row.get("ID"))
            description = description_to_html(row.get("description") or "")
            if description and "<br/>" not in description:
                extras = [
                    metadata_to_html("Platforms", row.get("platforms") or ""),
                    metadata_to_html("Data Sources", row.get("data sources") or ""),
                ]
                extras = [item for item in extras if item]
                if extras:
                    description = "<br/>".join([description] + extras)
            if attack_id and description:
                descriptions[attack_id] = description
    return descriptions


def main() -> int:
    descriptions = load_descriptions()
    updated = 0

    for path in sorted(TECHNIQUES_DIR.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        changed = False

        for tech in payload.get("techniques", []):
            if not is_generic_info_html(tech.get("info_html")):
                continue
            attack_id = extract_attack_id(tech)
            replacement = descriptions.get(attack_id) or MANUAL_DESCRIPTIONS.get(attack_id)
            if not replacement or replacement == tech.get("info_html"):
                continue
            tech["info_html"] = replacement
            updated += 1
            changed = True

        if changed:
            path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            print(f"updated {path.name}")

    print(f"total_updated={updated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
