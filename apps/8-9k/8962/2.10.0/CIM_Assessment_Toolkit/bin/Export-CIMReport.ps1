<#
.SYNOPSIS
    CIM Assessment Report Generator - Windows PowerShell Wrapper
    Machine Data Insights Inc.

    Copyright 2025-2026 Machine Data Insights Inc.
    Licensed under the Apache License, Version 2.0
    See LICENSE file for details.

.DESCRIPTION
    Exports CSV data from Splunk via REST API and generates a Word document report.

.PARAMETER Env
    Environment name displayed on the report (e.g., Production, Corp, QA)

.PARAMETER DataDir
    Directory containing pre-exported CSV files (manual mode)

.PARAMETER OutputDir
    Directory for the generated report (default: current directory)

.PARAMETER SplunkUri
    Splunk REST API base URI (e.g., https://localhost:8089)

.PARAMETER SplunkUser
    Splunk username (prompted if not provided with -SplunkUri)

.PARAMETER SplunkPass
    Splunk password as SecureString (prompted if not provided with -SplunkUri)

.EXAMPLE
    # Manual mode - CSVs already exported
    .\Export-CIMReport.ps1 -Env "Production" -DataDir "C:\CAT_Reports\data"

.EXAMPLE
    # Automated mode - pull from Splunk REST API
    .\Export-CIMReport.ps1 -Env "Corp-Prod" -SplunkUri "https://splunk:8089"

.EXAMPLE
    # Scheduled task (non-interactive)
    .\Export-CIMReport.ps1 -Env "Production" -SplunkUri "https://splunk:8089" -SplunkUser "svc_cat" -SplunkPass (ConvertTo-SecureString "password" -AsPlainText -Force) -OutputDir "C:\Reports"
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$Env = "Production",

    [string]$DataDir = "",
    [string]$OutputDir = ".",
    [string]$SplunkUri = "",
    [string]$SplunkUser = "",
    [SecureString]$SplunkPass = $null,
    [int]$TrendDays = 7,
    [string]$Scope = "all"
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ReportGen = Join-Path $ScriptDir "generate_report.py"
$Timestamp = Get-Date -Format "yyyyMMdd_HHmm"

# ── Verify Prerequisites ──────────────────────────────────────────────
Write-Host "CIM Assessment Report Generator" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan

# Check Python
$PythonBin = $null
foreach ($cmd in @("python3", "python")) {
    try {
        $pyVer = & $cmd --version 2>&1
        if ($pyVer -match "Python 3") {
            $PythonBin = $cmd
            Write-Host "Python: $pyVer" -ForegroundColor Green
            break
        }
    } catch {}
}
if (-not $PythonBin) {
    Write-Host "ERROR: Python 3 not found. Ensure python or python3 is in your PATH." -ForegroundColor Red
    exit 1
}

# Check report generator exists
if (-not (Test-Path $ReportGen)) {
    Write-Host "ERROR: generate_report.py not found at: $ReportGen" -ForegroundColor Red
    exit 1
}

# ── Setup Data Directory ──────────────────────────────────────────────
$CleanupData = $false
if ([string]::IsNullOrEmpty($DataDir)) {
    # Use a persistent directory next to the script for easy review
    $DataDir = Join-Path $ScriptDir "report_data"
    if (-not (Test-Path $DataDir)) {
        New-Item -ItemType Directory -Path $DataDir -Force | Out-Null
    }
    Write-Host "Data directory: $DataDir" -ForegroundColor Gray
}

if (-not (Test-Path $DataDir)) {
    New-Item -ItemType Directory -Path $DataDir -Force | Out-Null
}

# ── Splunk REST API Export ────────────────────────────────────────────
if (-not [string]::IsNullOrEmpty($SplunkUri)) {
    Write-Host "`nPulling data from Splunk: $SplunkUri" -ForegroundColor Cyan

    # Get credentials
    if ([string]::IsNullOrEmpty($SplunkUser)) {
        $SplunkUser = Read-Host "Splunk username"
    }
    if ($null -eq $SplunkPass) {
        $SplunkPass = Read-Host "Splunk password" -AsSecureString
    }

    $Credential = New-Object System.Management.Automation.PSCredential($SplunkUser, $SplunkPass)

    # Allow self-signed certs
    if (-not ([System.Management.Automation.PSTypeName]'TrustAllCertsPolicy').Type) {
        Add-Type @"
using System.Net;
using System.Security.Cryptography.X509Certificates;
public class TrustAllCertsPolicy : ICertificatePolicy {
    public bool CheckValidationResult(ServicePoint sp, X509Certificate cert, WebRequest req, int problem) { return true; }
}
"@
    }
    [System.Net.ServicePointManager]::CertificatePolicy = New-Object TrustAllCertsPolicy
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.SecurityProtocolType]::Tls12

    function Invoke-SplunkSearch {
        param([string]$Search, [string]$OutFile, [string]$Earliest = "-24h@h", [string]$Latest = "now")

        $fileName = Split-Path -Leaf $OutFile
        Write-Host "  Exporting: $fileName..." -ForegroundColor Gray -NoNewline

        $body = @{
            search = $Search
            earliest_time = $Earliest
            latest_time = $Latest
            output_mode = "csv"
        }

        try {
            $response = Invoke-WebRequest `
                -Uri "$SplunkUri/services/search/jobs/export" `
                -Method POST `
                -Body $body `
                -Credential $Credential `
                -UseBasicParsing

            $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
            [System.IO.File]::WriteAllText($OutFile, $response.Content, $utf8NoBom)
            $size = (Get-Item $OutFile).Length
            Write-Host " ($size bytes)" -ForegroundColor $(if ($size -gt 10) { "Green" } else { "Yellow" })
        } catch {
            Write-Host " FAILED" -ForegroundColor Red
            Write-Host "    $($_.Exception.Message)" -ForegroundColor Yellow
        }
    }

    # Clear stale files from previous runs
    Get-ChildItem -Path $DataDir -Filter "*.csv" -ErrorAction SilentlyContinue | Remove-Item -Force
    Write-Host "  Cleared previous export data" -ForegroundColor Gray

    # KPI Summary
    Invoke-SplunkSearch -OutFile (Join-Path $DataDir "kpi.csv") -Search @'
search `cim_validator_base_search` | eval percent_coverage = if(percent_coverage > 100, 100, percent_coverage) | bin _time span=1d | eval is_rec = if(field_class IN ("required", "recommended"), 1, 0) | eval is_rec_mapped = if(is_rec=1 AND field_count > 0, 1, 0) | eval has_pv = if(isnotnull(value_compliance_pct), 1, 0) | eval pv_compliant = if(has_pv=1 AND value_compliance_pct >= 80, 1, 0) | eventstats sum(is_rec) as total_rec_fields sum(is_rec_mapped) as mapped_rec_fields avg(eval(if(is_rec=1, percent_coverage, null()))) as percent_data_coverage sum(has_pv) as total_pv_fields sum(pv_compliant) as compliant_pv_fields by modelName dataset index sourcetype | eval rec_field_coverage_pct = round(mapped_rec_fields / total_rec_fields * 100, 2) | eval percent_data_coverage = round(percent_data_coverage, 2) | eval value_quality_pct = if(total_pv_fields > 0, round(compliant_pv_fields / total_pv_fields * 100, 2), null()) | eval overall_quality_pct = round((rec_field_coverage_pct + percent_data_coverage) / 2, 2) | dedup modelName dataset index sourcetype | stats avg(rec_field_coverage_pct) as mapping_quality avg(percent_data_coverage) as data_quality avg(eval(if(isnotnull(value_quality_pct), value_quality_pct, null()))) as value_compliance avg(overall_quality_pct) as overall_quality | eval mapping_quality=round(mapping_quality,1) | eval data_quality=round(data_quality,1) | eval value_compliance=round(value_compliance,1) | eval overall_quality=round(overall_quality,1)
'@

    # Compliance Detail (model/dataset)
    Invoke-SplunkSearch -OutFile (Join-Path $DataDir "compliance_detail.csv") -Search @'
search `cim_validator_base_search` | eval percent_coverage = if(percent_coverage > 100, 100, percent_coverage) | bin _time span=1d | eval is_rec = if(field_class IN ("required", "recommended"), 1, 0) | eval is_rec_mapped = if(is_rec=1 AND field_count > 0, 1, 0) | eventstats sum(is_rec) as total_rec_fields sum(is_rec_mapped) as mapped_rec_fields avg(eval(if(is_rec=1, percent_coverage, null()))) as percent_data_coverage by modelName dataset index sourcetype | eval rec_field_coverage_pct = round(mapped_rec_fields / total_rec_fields * 100, 2) | eval percent_data_coverage = round(percent_data_coverage, 2) | eval overall_quality_pct = round((rec_field_coverage_pct + percent_data_coverage) / 2, 2) | dedup modelName dataset index sourcetype | stats avg(rec_field_coverage_pct) as "Mapping %" avg(percent_data_coverage) as "Data Quality %" avg(overall_quality_pct) as "Overall %" dc(index) as indexes dc(sourcetype) as sourcetypes by modelName dataset | eval "Mapping %" = round('Mapping %', 1) | eval "Data Quality %" = round('Data Quality %', 1) | eval "Overall %" = round('Overall %', 1) | rename modelName as "Data Model" dataset as "Dataset" | sort "Data Model" Dataset
'@

    # Compliance Summary (by data source)
    Invoke-SplunkSearch -OutFile (Join-Path $DataDir "compliance_summary.csv") -Search @'
search `cim_validator_base_search` | eval percent_coverage = if(percent_coverage > 100, 100, percent_coverage) | bin _time span=1d | eval is_rec = if(field_class IN ("required", "recommended"), 1, 0) | eval is_rec_mapped = if(is_rec=1 AND field_count > 0, 1, 0) | eval has_pv = if(isnotnull(value_compliance_pct), 1, 0) | eval pv_compliant = if(has_pv=1 AND value_compliance_pct >= 80, 1, 0) | eventstats sum(is_rec) as total_rec_fields sum(is_rec_mapped) as mapped_rec_fields avg(eval(if(is_rec=1, percent_coverage, null()))) as percent_data_coverage max(total_count) as event_count sum(has_pv) as total_pv_fields sum(pv_compliant) as compliant_pv_fields values(eval(if(is_rec=1 AND is_rec_mapped=0, field, null()))) as missing_rec_fields by modelName dataset index sourcetype | eval rec_field_coverage_pct = round(mapped_rec_fields / total_rec_fields * 100, 2) | eval percent_data_coverage = round(percent_data_coverage, 2) | eval value_quality_pct = if(total_pv_fields > 0, round(compliant_pv_fields / total_pv_fields * 100, 2), null()) | eval overall_quality_pct = round((rec_field_coverage_pct + percent_data_coverage) / 2, 2) | dedup modelName dataset index sourcetype | rename modelName as "Data Model" dataset as "Dataset" rec_field_coverage_pct as "Mapping %" percent_data_coverage as "Data Quality %" value_quality_pct as "Value Compliance" overall_quality_pct as "Overall %" event_count as "Events" missing_rec_fields as "Missing Fields" | table "Data Model" Dataset index sourcetype "Mapping %" "Data Quality %" "Value Compliance" "Overall %" Events "Missing Fields" | sort "Data Model" Dataset sourcetype
'@

    # Field Gaps — aggregate across indexes to one row per model/dataset/sourcetype/field
    Invoke-SplunkSearch -OutFile (Join-Path $DataDir "field_gaps.csv") -Search @'
search `cim_validator_base_search` | eval percent_coverage = if(percent_coverage > 100, 100, percent_coverage) | search field_class IN ("required", "recommended") | stats max(total_count) as total_count sum(field_count) as field_count max(distinct_count) as distinct_count avg(percent_coverage) as percent_coverage latest(field_class) as field_class sum(compliant_count) as compliant_count avg(value_compliance_pct) as value_compliance_pct by modelName dataset sourcetype field | eval pv_rounded = round(value_compliance_pct, 1) | where field_count=0 OR (isnotnull(value_compliance_pct) AND pv_rounded < 100) | eval pv_display = if(isnotnull(value_compliance_pct), tostring(pv_rounded)."%", "---") | fields - pv_rounded | rename modelName as "Data Model" dataset as "Dataset" field as "Field" field_class as "Class" field_count as "Count" percent_coverage as "Coverage %" pv_display as "Value Compliance" | table "Data Model" Dataset sourcetype Field Class Count "Coverage %" "Value Compliance" | sort "Data Model" Dataset sourcetype -Class Field
'@

    # Scope filter applied to both unmapped and mapped sourcetype lists so
    # they match the dashboard's scope-aware Mapped/Unmapped counts.
    $scopeClause = if ($Scope -ne "all") { ' | where like(scope, "%' + $Scope + '%")' } else { '' }

    # Unmapped Sourcetypes - enriched with inventory lookup
    $unmappedSpl = @'
| tstats count WHERE index=* NOT index=_* NOT index=`cim_validator_index` BY sourcetype | join type=left sourcetype [| search `cim_validator_base_search` | stats dc(modelName) as model_count values(modelName) as mapped_models by sourcetype] | eval is_mapped = if(isnotnull(model_count) AND model_count > 0, "Yes", "No") | search is_mapped="No" | lookup cim_sourcetype_inventory sourcetype OUTPUT vendor, tech_category, security_relevance, scope | join type=left sourcetype [| inputlookup cim_sourcetype_exclusions | eval exclude = if(match(lower(trim(exclude)), "^(n|no|f|false|0)$"), "N", "Y") | fields sourcetype exclude] | eval exclude = if(isnull(exclude), "N", exclude) | where exclude!="Y" | eval security_relevance = if(isnotnull(security_relevance), security_relevance, "unknown") | eval vendor = if(isnotnull(vendor), vendor, "") | eval scope = if(isnotnull(scope), scope, "unknown")<SCOPE_CLAUSE> | eval relevance_sort = case(security_relevance="high", 0, security_relevance="med", 1, security_relevance="low", 2, security_relevance="none", 3, 1=1, 4) | sort relevance_sort vendor sourcetype | fields - relevance_sort exclude | eval tech_category = if(isnotnull(tech_category), tech_category, "") | rename count as "Events" vendor as "Vendor" security_relevance as "Relevance" scope as "Scope" tech_category as "Tech Category" | table sourcetype Events Vendor "Tech Category" Relevance Scope
'@.Replace('<SCOPE_CLAUSE>', $scopeClause)
    Invoke-SplunkSearch -OutFile (Join-Path $DataDir "unmapped.csv") -Search $unmappedSpl

    # Mapped Sourcetypes - enriched with inventory lookup
    $mappedSpl = @'
| tstats count WHERE index=* NOT index=_* NOT index=`cim_validator_index` BY sourcetype | join type=left sourcetype [| search `cim_validator_base_search` | stats dc(modelName) as model_count values(modelName) as mapped_models by sourcetype] | eval is_mapped = if(isnotnull(model_count) AND model_count > 0, "Yes", "No") | search is_mapped="Yes" | lookup cim_sourcetype_inventory sourcetype OUTPUT vendor, security_relevance, scope | eval security_relevance = if(isnotnull(security_relevance), security_relevance, "unknown") | eval vendor = if(isnotnull(vendor), vendor, "") | eval scope = if(isnotnull(scope), scope, "unknown")<SCOPE_CLAUSE> | eval mapped_list = mvjoin(mapped_models, ", ") | eval relevance_sort = case(security_relevance="high", 0, security_relevance="med", 1, security_relevance="low", 2, security_relevance="none", 3, 1=1, 4) | sort relevance_sort vendor sourcetype | fields - relevance_sort | rename count as "Events" vendor as "Vendor" security_relevance as "Relevance" scope as "Scope" mapped_list as "Mapped To" | table sourcetype Vendor Relevance Scope Events "Mapped To"
'@.Replace('<SCOPE_CLAUSE>', $scopeClause)
    Invoke-SplunkSearch -OutFile (Join-Path $DataDir "mapped.csv") -Search $mappedSpl

    # Remediation Priorities
    Invoke-SplunkSearch -OutFile (Join-Path $DataDir "remediation.csv") -Search @'
search `cim_validator_base_search` | eval percent_coverage = if(percent_coverage > 100, 100, percent_coverage) | search field_class IN ("required", "recommended") | bin _time span=1d | eval is_mapped = if(field_count > 0, 1, 0) | stats sum(is_mapped) as mapped_rec_fields dc(field) as total_rec_fields avg(percent_coverage) as percent_data_coverage max(total_count) as event_count values(eval(if(is_mapped=0, field, null()))) as missing_rec_fields avg(eval(if(isnotnull(value_compliance_pct), value_compliance_pct, null()))) as avg_value_compliance by modelName dataset index sourcetype | eval rec_field_coverage_pct = round(mapped_rec_fields / total_rec_fields * 100, 2) | eval percent_data_coverage = round(percent_data_coverage, 2) | eval overall_quality_pct = round((rec_field_coverage_pct + percent_data_coverage) / 2, 2) | eval priority_score = round((100 - overall_quality_pct) * log(event_count + 1), 2) | eval missing_rec_count = mvcount(missing_rec_fields) | fillnull value=0 missing_rec_count | lookup splunk_data_model_objects_fields model as modelName dataset OUTPUT constraints | eval required_tags = mvdedup(constraints) | eval required_tags = mvindex(required_tags, 0) | rex field=required_tags "tag=(?<required_tags>.+)" | rename modelName as "Data Model" dataset as "Dataset" overall_quality_pct as "Overall %" rec_field_coverage_pct as "Mapping %" event_count as "Events" priority_score as "Priority" missing_rec_count as "Missing #" required_tags as "Required Tags" | where Priority > 0 | table "Data Model" Dataset sourcetype "Overall %" "Mapping %" Events Priority "Missing #" "Required Tags" | sort "Data Model" Dataset sourcetype
'@

    # Compliance Trends (prior snapshot - 3-day window centered on target day)
    $trendEarliest = "-$($TrendDays + 2)d@d"
    $trendLatest = "-$([Math]::Max($TrendDays - 1, 1))d@d"
    Invoke-SplunkSearch -Earliest $trendEarliest -Latest $trendLatest -OutFile (Join-Path $DataDir "trends.csv") -Search @'
search `cim_validator_base_search` | bin _time span=1d | eval is_rec = if(field_class IN ("required", "recommended"), 1, 0) | eval is_rec_mapped = if(is_rec=1 AND field_count > 0, 1, 0) | eventstats sum(is_rec) as total_rec_fields sum(is_rec_mapped) as mapped_rec_fields avg(eval(if(is_rec=1, percent_coverage, null()))) as percent_data_coverage by modelName dataset index sourcetype | eval rec_field_coverage_pct = round(mapped_rec_fields / total_rec_fields * 100, 2) | eval percent_data_coverage = round(percent_data_coverage, 2) | eval overall_quality_pct = round((rec_field_coverage_pct + percent_data_coverage) / 2, 2) | dedup modelName dataset index sourcetype | stats latest(overall_quality_pct) as "Prior Overall %" by modelName dataset | eval "Prior Overall %" = round('Prior Overall %', 1) | rename modelName as "Data Model" dataset as "Dataset"
'@

    # Acceleration Health - query each CIM model individually
    # The listing endpoint returns 0 entries, but individual lookups work
    Write-Host "  Exporting: acceleration.csv (per-model REST)..." -ForegroundColor Gray -NoNewline
    try {
        # Standard CIM data models with their summarization names
        $cimModels = @(
            "Alerts", "Authentication", "Certificates", "Change", "Compute_Inventory",
            "DLP", "Databases", "Email", "Endpoint", "Event_Signatures",
            "Interprocess_Messaging", "Intrusion_Detection", "JVM", "Malware",
            "Network_Resolution", "Network_Sessions", "Network_Traffic",
            "Performance", "Splunk_Audit", "Ticket_Management",
            "Updates", "Vulnerabilities", "Web"
        )

        $csvLines = @('"Data Model",app,status,"Complete %",Earliest,Latest,"Retention (days)",Searches,"Last Error"')
        $foundCount = 0

        foreach ($model in $cimModels) {
            $summaryName = "tstats:DM_Splunk_SA_CIM_$model"
            $encodedName = [System.Uri]::EscapeDataString($summaryName)

            try {
                $modelResponse = Invoke-WebRequest `
                    -Uri "$SplunkUri/services/admin/summarization/$($encodedName)?output_mode=json" `
                    -Method GET `
                    -Credential $Credential `
                    -UseBasicParsing `
                    -TimeoutSec 10

                $modelJson = $modelResponse.Content | ConvertFrom-Json
                if ($modelJson.entry.Count -eq 0) { continue }

                $c = $modelJson.entry[0].content
                $completePct = [math]::Round(($c.'summary.complete' + 0) * 100, 1)
                $isBuilding = $c.'summary.is_inprogress' + 0
                $lastError = if ($c.'summary.last_error') { "$($c.'summary.last_error')" } else { "" }
                $status = if ($lastError -and $lastError -ne "None" -and $lastError -ne "") { "Error" }
                          elseif ($completePct -ge 99.9) { "Complete" }
                          elseif ($isBuilding -eq 1) { "Building" }
                          else { "Incomplete" }

                $eTime = $c.'summary.earliest_time'
                $lTime = $c.'summary.latest_time'
                $earliest = if ($eTime -and $eTime -gt 0) {
                    [DateTimeOffset]::FromUnixTimeSeconds([long]$eTime).DateTime.ToString("yyyy-MM-dd HH:mm")
                } else { "N/A" }
                $latest = if ($lTime -and $lTime -gt 0) {
                    [DateTimeOffset]::FromUnixTimeSeconds([long]$lTime).DateTime.ToString("yyyy-MM-dd HH:mm")
                } else { "N/A" }

                $ret = $c.'summary.time_range'
                if (-not $ret) { $ret = $c.'summary.retention' }
                $retDays = if ($ret -and $ret -gt 0) { [math]::Round($ret / 86400, 1) } else { "N/A" }

                $searches = if ($c.'summary.access_count') { $c.'summary.access_count' } else { 0 }

                $csvLines += "`"$model`",Splunk_SA_CIM,$status,$completePct,$earliest,$latest,$retDays,$searches,`"$lastError`""
                $foundCount++
            } catch {
                # Model not accelerated or doesn't exist - skip silently
                continue
            }
        }

        $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
        [System.IO.File]::WriteAllText((Join-Path $DataDir "acceleration.csv"), ($csvLines -join "`n"), $utf8NoBom)
        $size = (Get-Item (Join-Path $DataDir "acceleration.csv")).Length
        Write-Host " ($size bytes, $foundCount models)" -ForegroundColor $(if ($foundCount -gt 0) { "Green" } else { "Yellow" })
    } catch {
        Write-Host " FAILED" -ForegroundColor Red
        Write-Host "    $($_.Exception.Message)" -ForegroundColor Yellow
    }

    Write-Host "`nData export complete." -ForegroundColor Green
    Write-Host "Data directory: $DataDir" -ForegroundColor Gray
}

# ── Verify Required Files ─────────────────────────────────────────────
$RequiredFiles = @("kpi.csv", "compliance_detail.csv", "compliance_summary.csv",
                   "field_gaps.csv", "mapped.csv", "remediation.csv", "acceleration.csv")
$Missing = 0

foreach ($f in $RequiredFiles) {
    $fpath = Join-Path $DataDir $f
    if (-not (Test-Path $fpath)) {
        Write-Host "WARNING: Missing $f" -ForegroundColor Yellow
        $Missing++
    }
}

# Create unmapped.csv if missing (may legitimately be empty)
$unmappedPath = Join-Path $DataDir "unmapped.csv"
if (-not (Test-Path $unmappedPath)) {
    "sourcetype,Events,Vendor,Relevance,Scope" | Out-File -Encoding utf8 $unmappedPath
}

if ($Missing -gt 1) {
    Write-Host "`nMissing CSV files. For manual export, run the SPL queries from" -ForegroundColor Red
    Write-Host "README_Report.md and save CSVs to: $DataDir" -ForegroundColor Red
    exit 1
}

# ── Generate Report ───────────────────────────────────────────────────
if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
}

$ScopeLabel = if ($Scope -ne "all") { "_$($Scope.Substring(0,1).ToUpper() + $Scope.Substring(1))" } else { "" }
$OutputFile = Join-Path $OutputDir "CIM_Assessment_Report_${Env}${ScopeLabel}_${Timestamp}.docx"

Write-Host "`nGenerating report: $OutputFile" -ForegroundColor Cyan
Write-Host "  Using: $PythonBin generate_report.py" -ForegroundColor Gray
Write-Host "  Scope: $Scope" -ForegroundColor Gray
& $PythonBin $ReportGen --env $Env --data-dir $DataDir --output $OutputFile --trend-days $TrendDays --scope $Scope

if ($LASTEXITCODE -eq 0) {
    Write-Host "`nReport generated successfully!" -ForegroundColor Green
    Write-Host "  $OutputFile" -ForegroundColor White

    # Open report
    $openChoice = Read-Host "`nOpen report now? (Y/n)"
    if ($openChoice -ne "n" -and $openChoice -ne "N") {
        Start-Process $OutputFile
    }
} else {
    Write-Host "`nERROR: Report generation failed." -ForegroundColor Red
    exit 1
}

# CSVs retained in: $DataDir (for manual review)
