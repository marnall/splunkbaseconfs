<#
    TA-windows-firewall-posture
    Emits the enabled Windows Defender Firewall rules, flattened with their
    port, address and application filters.

    One event per rule, key=value, consumed as sourcetype
    windows:firewall:rule.

    This is an inventory, not an event stream: schedule it daily, not hourly.
    A typical workstation has 200-400 enabled rules.

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

# Only enabled rules by default. Set to $false to inventory everything.
$OnlyEnabled = $true

function Get-Value {
    param($Value, $Default = 'any')
    if ($null -eq $Value) { return $Default }
    $s = ($Value -join ',')
    if ([string]::IsNullOrWhiteSpace($s)) { return $Default }
    return $s
}

try {
    $computer  = $env:COMPUTERNAME
    $collected = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')

    $rules = Get-NetFirewallRule -PolicyStore ActiveStore
    if ($OnlyEnabled) { $rules = $rules | Where-Object { $_.Enabled -eq 'True' } }

    # One bulk call each, then index by InstanceID: per-rule piping is
    # roughly 50x slower on a machine with several hundred rules.
    $portFilters = @{}
    Get-NetFirewallPortFilter -PolicyStore ActiveStore |
        ForEach-Object { $portFilters[$_.InstanceID] = $_ }
    $addrFilters = @{}
    Get-NetFirewallAddressFilter -PolicyStore ActiveStore |
        ForEach-Object { $addrFilters[$_.InstanceID] = $_ }
    $appFilters = @{}
    Get-NetFirewallApplicationFilter -PolicyStore ActiveStore |
        ForEach-Object { $appFilters[$_.InstanceID] = $_ }

    foreach ($r in $rules) {
        $pf = $portFilters[$r.InstanceID]
        $af = $addrFilters[$r.InstanceID]
        $ap = $appFilters[$r.InstanceID]

        $localPort  = Get-Value $pf.LocalPort
        $remotePort = Get-Value $pf.RemotePort
        $protocol   = Get-Value $pf.Protocol
        $localAddr  = Get-Value $af.LocalAddress
        $remoteAddr = Get-Value $af.RemoteAddress
        $program    = Get-Value $ap.Program
        $direction  = "$($r.Direction)".ToLower()
        $ruleAction = "$($r.Action)".ToLower()

        # Risk scoring: an inbound allow rule open to any address, on any port,
        # with no application binding is the shape you want to find.
        $risks = New-Object System.Collections.ArrayList
        if ($direction -eq 'inbound' -and $ruleAction -eq 'allow') {
            if ($remoteAddr -eq 'any')                     { [void]$risks.Add('inbound_allow_any_source') }
            if ($localPort  -eq 'any')                     { [void]$risks.Add('inbound_allow_any_port') }
            if ($program    -eq 'any')                     { [void]$risks.Add('inbound_allow_no_application') }
            if ($remoteAddr -eq 'any' -and $localPort -eq 'any' -and $program -eq 'any') {
                [void]$risks.Add('inbound_allow_any_any_any')
            }
        }
        if ($ruleAction -eq 'allow' -and $localPort -match '\b(3389|445|5985|5986|22|23|1433|3306|5432)\b' `
            -and $direction -eq 'inbound' -and $remoteAddr -eq 'any') {
            [void]$risks.Add('administrative_port_open_to_any')
        }

        $severity = 'informational'
        if ($risks -contains 'inbound_allow_any_any_any')      { $severity = 'high' }
        elseif ($risks -contains 'administrative_port_open_to_any') { $severity = 'critical' }
        elseif ($risks.Count -gt 0)                            { $severity = 'medium' }

        $fields = [ordered]@{
            collected_time = $collected
            Computer       = $computer
            rule_name      = $r.DisplayName
            rule_id        = $r.Name
            rule_group     = Get-Value $r.DisplayGroup '-'
            enabled        = "$($r.Enabled)".ToLower()
            direction      = $direction
            rule_action    = $ruleAction
            profile        = Get-Value $r.Profile 'any'
            protocol       = $protocol
            local_port     = $localPort
            remote_port    = $remotePort
            local_address  = $localAddr
            remote_address = $remoteAddr
            program        = $program
            policy_source  = Get-Value $r.PolicyStoreSourceType '-'
            edge_traversal = "$($r.EdgeTraversalPolicy)".ToLower()
            risks          = ($risks -join ',')
            risk_count     = $risks.Count
            severity       = $severity
        }

        ConvertTo-KvLine $fields
    }
}
catch {
    "collected_time=$((Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')) Computer=$env:COMPUTERNAME log_level=ERROR message=""$($_.Exception.Message -replace '"','\"')"""
}
