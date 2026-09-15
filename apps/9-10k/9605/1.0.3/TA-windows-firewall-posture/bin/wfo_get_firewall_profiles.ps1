<#
    TA-windows-firewall-posture
    Emits the current state of the three Windows Defender Firewall profiles.

    One event per profile, key=value, consumed as sourcetype
    windows:firewall:profile.

    Read only: this script queries the firewall configuration and never
    modifies it.
#>

$ErrorActionPreference = 'Stop'

function ConvertTo-KvLine {
    <#
        Serialises an ordered dictionary into a Splunk friendly key=value line.
        Splunk auto key=value parsing has no escape sequence for an embedded
        double quote, so embedded quotes become single quotes rather than being
        escaped. Empty values become "-" so the field still exists.
    #>
    param([System.Collections.Specialized.OrderedDictionary]$Fields)
    ($Fields.GetEnumerator() | ForEach-Object {
        $v = "$($_.Value)"
        $v = $v -replace '"', "'"
        if ($v -eq '') { $v = '-' }
        if ($v -match '[\s,=]') { "$($_.Key)=`"$v`"" } else { "$($_.Key)=$v" }
    }) -join ' '
}

function ConvertTo-Bool {
    param($Value)
    switch ("$Value") {
        'True'      { 'true';  break }
        'False'     { 'false'; break }
        'Enabled'   { 'true';  break }
        'Disabled'  { 'false'; break }
        'NotConfigured' { 'notconfigured'; break }
        default     { "$Value".ToLower() }
    }
}

try {
    $computer  = $env:COMPUTERNAME
    $collected = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')

    try   { $service = (Get-Service -Name MpsSvc -ErrorAction Stop).Status.ToString().ToLower() }
    catch { $service = 'unknown' }

    foreach ($p in Get-NetFirewallProfile -PolicyStore ActiveStore) {

        $logFile  = $p.LogFileName
        $logSize  = 0
        $logExists = 'false'
        if ($logFile) {
            $resolved = [System.Environment]::ExpandEnvironmentVariables($logFile)
            if (Test-Path -LiteralPath $resolved) {
                $logExists = 'true'
                $logSize   = [int]((Get-Item -LiteralPath $resolved).Length / 1KB)
            }
        }

        $enabled     = ConvertTo-Bool $p.Enabled
        $logAllowed  = ConvertTo-Bool $p.LogAllowed
        $logBlocked  = ConvertTo-Bool $p.LogBlocked
        $inbound     = "$($p.DefaultInboundAction)".ToLower()
        $outbound    = "$($p.DefaultOutboundAction)".ToLower()

        # Compliance checks, so the search head does not have to re-derive them.
        $findings = New-Object System.Collections.ArrayList
        if ($enabled    -ne 'true')  { [void]$findings.Add('firewall_disabled') }
        if ($logBlocked -ne 'true')  { [void]$findings.Add('dropped_packets_not_logged') }
        if ($logAllowed -ne 'true')  { [void]$findings.Add('allowed_connections_not_logged') }
        if ($inbound    -eq 'allow') { [void]$findings.Add('default_inbound_allow') }
        if ($p.LogMaxSizeKilobytes -lt 20480) { [void]$findings.Add('log_size_below_20mb') }
        if ($logExists  -ne 'true')  { [void]$findings.Add('log_file_missing') }

        $compliant = if ($findings.Count -eq 0) { 'true' } else { 'false' }

        $fields = [ordered]@{
            collected_time            = $collected
            Computer                  = $computer
            firewall_service          = $service
            profile                   = $p.Name
            enabled                   = $enabled
            default_inbound_action    = $inbound
            default_outbound_action   = $outbound
            log_allowed               = $logAllowed
            log_blocked               = $logBlocked
            log_max_size_kb           = $p.LogMaxSizeKilobytes
            log_file_name             = $logFile
            log_file_present          = $logExists
            log_file_size_kb          = $logSize
            notify_on_listen          = (ConvertTo-Bool $p.NotifyOnListen)
            allow_inbound_rules       = (ConvertTo-Bool $p.AllowInboundRules)
            allow_local_firewall_rules = (ConvertTo-Bool $p.AllowLocalFirewallRules)
            allow_local_ipsec_rules   = (ConvertTo-Bool $p.AllowLocalIPsecRules)
            allow_unicast_response    = (ConvertTo-Bool $p.AllowUnicastResponseToMulticast)
            compliant                 = $compliant
            findings                  = ($findings -join ',')
            finding_count             = $findings.Count
        }

        ConvertTo-KvLine $fields
    }
}
catch {
    "collected_time=$((Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')) Computer=$env:COMPUTERNAME log_level=ERROR message=""$($_.Exception.Message -replace '"','\"')"""
}
