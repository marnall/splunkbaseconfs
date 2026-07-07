<#
    .SYNOPSIS
    Get Certificate data from one or more certificate athorities.

    All Available Fields
        PSPath
        PSParentPath
        PSChildName
        IssuerName
        HasPrivateKey
        SubjectName
        FriendlyName
        Issuer
        NotAfter
        NotBefore
        SerialNumber
        Thumbprint
        EnhancedKeyUsageList
        PSDrive
        PSProvider
        PSIsContainer
        PrivateKey
        PublicKey
        RawData
        SendAsTrustedIssuer
        EnrollmentServerEndPoint
        Extensions
        EnrollmentPolicyEndPoint
        DnsNameList
        Subject
        SignatureAlgorithm
        Version
        PolicyId
        Handle
        Archived

    Default excluded fields
        PSIsContainer
        PrivateKey
        RawData
        PSDrive
        PSProvider
        PublicKey
        EnhancedKeyUsageList
        EnrollmentServerEndPoint
        EnrollmentPolicyEndPoint
        SendAsTrustedIssuer
        Extensions
        PolicyId
        Handle
        Archived

    Note: included fields will vary depending on cert type and properties included in the cert
#>


$array = @()

Get-ChildItem -path cert:\LocalMachine -recurse |
    where-object  { -not $_.PSIsContainer} |
    foreach-object ({
        if($_.DnsNameList){$DnsNameList = [system.String]::Join(",", $_.DnsNameList)} else { $DnsNameList = "" }
        if($_.PSPath){$PSPath = [system.String]::Join(",", $_.PSPath)} else { $PSPath = "" }
        if($_.PSParentPath){$PSParentPath = [system.String]::Join(",", $_.PSParentPath)} else { $PSParentPath = "" }
        if($_.PSChildName){$PSChildName = [system.String]::Join(",", $_.PSChildName)} else { $PSChildName = "" }
        if($_.IssuerName){$IssuerName = [system.String]::Join(",", $_.IssuerName)} else { $IssuerName = "" }
        if($_.HasPrivateKey){$HasPrivateKey = [system.String]::Join(",", $_.HasPrivateKey)} else { $HasPrivateKey = "" }
        if($_.SubjectName){$SubjectName = [system.String]::Join(",", $_.SubjectName)} else { $SubjectName = "" }
        if($_.FriendlyName){$FriendlyName = [system.String]::Join(",", $_.FriendlyName)} else { $FriendlyName = "" }
        if($_.Issuer){$Issuer = [system.String]::Join(",", $_.Issuer)} else { $Issuer = "" }
        if($_.NotAfter){$NotAfter = [system.String]::Join(",", $_.NotAfter)} else { $NotAfter = "" }
        if($_.NotBefore){$NotBefore = [system.String]::Join(",", $_.NotBefore)} else { $NotBefore = "" }
        if($_.SerialNumber){$SerialNumber = [system.String]::Join(",", $_.SerialNumber)} else { $SerialNumber = "" }
        if($_.Thumbprint){$Thumbprint = [system.String]::Join(",", $_.Thumbprint)} else { $Thumbprint = "" }
        if($_.Subject){$Subject = [system.String]::Join(",", $_.Subject)} else { $Subject = "" }
        if($_.SignatureAlgorithm){$SignatureAlgorithm = [system.String]::Join(",", $_.SignatureAlgorithm)} else { $SignatureAlgorithm = "" }
        if($_.Version){$Version = [system.String]::Join(",", $_.Version)} else { $Version = "" }

        $obj = New-Object -TypeName PSObject
        $obj | Add-Member -MemberType NoteProperty  -Name "PSPath" -Value "$PSPath"
        $obj | Add-Member -MemberType NoteProperty  -Name "PSParentPath" -Value "$PSParentPath"
        $obj | Add-Member -MemberType NoteProperty  -Name "PSChildName" -Value "$PSChildName"
        $obj | Add-Member -MemberType NoteProperty  -Name "IssuerName" -Value "$IssuerName"
        $obj | Add-Member -MemberType NoteProperty  -Name "HasPrivateKey" -Value "$HasPrivateKey"
        $obj | Add-Member -MemberType NoteProperty  -Name "SubjectName" -Value "$SubjectName"
        $obj | Add-Member -MemberType NoteProperty  -Name "FriendlyName" -Value "$FriendlyName"
        $obj | Add-Member -MemberType NoteProperty  -Name "Issuer" -Value "$Issuer"
        $obj | Add-Member -MemberType NoteProperty  -Name "NotAfter" -Value "$NotAfter"
        $obj | Add-Member -MemberType NoteProperty  -Name "NotBefore" -Value "$NotBefore"
        $obj | Add-Member -MemberType NoteProperty  -Name "SerialNumber" -Value "$SerialNumber"
        $obj | Add-Member -MemberType NoteProperty  -Name "Thumbprint" -Value "$Thumbprint"
        $obj | Add-Member -MemberType NoteProperty  -Name "DnsNameList" -Value "$DnsNameList"
        $obj | Add-Member -MemberType NoteProperty  -Name "Subject" -Value "$Subject"
        $obj | Add-Member -MemberType NoteProperty  -Name "Version" -Value "$Version"
        $obj | Add-Member -MemberType NoteProperty  -Name "SignatureAlgorithm" -Value "$SignatureAlgorithm"
 $array += $obj
    })
$array | Select-Object *
