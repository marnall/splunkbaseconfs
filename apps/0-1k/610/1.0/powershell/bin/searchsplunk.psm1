## Copyright 2011 Michael Vierling

$SCRIPT:credentials = $null

function Search-Splunk
{
    param(
        [Parameter(ValueFromPipeline = $true)]
        $SearchString,
        [Parameter(Mandatory = $false)]
        [string[]] $Port = '8089',
        [Parameter(Mandatory = $false)]
        [string[]] $Host = 'splunk.yellowpages.com',
        [Parameter(Mandatory = $false)]
        [string[]] $Option = "",
        [Parameter(Mandatory = $false)]
        [System.Net.NetworkCredential] $Credentials
    )

    begin
    {
        $SCRIPT:credentials = new-object System.Net.NetworkCredential('search_user','password')
    }

    process
    {
        $request = 'https://' + $Host + ":" + $Port + '/services/search/jobs/export'
        $post = '?search=search ' + $SearchString + '&exec_mode=oneshot' + $Option
        $request_post = $request + $post
        $splunk = new-object System.Net.WebClient
        $splunk.Credentials = $SCRIPT:credentials
        [System.Net.ServicePointManager]::ServerCertificateValidationCallback = {$true}
        $page = $splunk.DownloadString($request_post.ToString())
        $page
    }
}

Export-ModuleMember -Function Search-Splunk
