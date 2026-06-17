// Copyright 2011 - Michael Vierling

(*
To use this module from Powershell, follow this example:

ps>Search-Splunk "My splunk search query" -Host "splunk.yellowpages.com" -Port "8089" -Option "&max_count=100"
*)

module SplunkSearch

open System
open System.Net
open System.Security
open System.Management.Automation

type TrustAll() =
    interface System.Net.ICertificatePolicy with
        member this.CheckValidationResult( p, s, w, i ) = true;;

[<Cmdlet(System.Management.Automation.VerbsCommon.Search,"Splunk")>]
type public MyWriteInputObjectCmdlet() =
    inherit Cmdlet()

    let mutable _Port = "8089"
    let mutable _Host = "splunk.yellowpages.com"
    let mutable _SearchString = ""
    let mutable _Credentials = new System.Net.NetworkCredential( "search_user", "password" )
    let mutable _Option = ""

    [<Parameter(Mandatory=true, Position = 0, ValueFromPipeline = true)>]
    member this.SearchString
        with get() = _SearchString
        and set(v) = _SearchString <- v
    [<Parameter(Mandatory=false)>]
    member this.Port
        with get() = _Port
        and set(v) = _Port <- v

    [<Parameter(Mandatory=false)>]
    member this.Host
        with get() = _Host
        and set(v) = _Host <- v

    [<Parameter(Mandatory=false)>]
    member this.Credentials
        with get() = _Credentials
        and set(v) = _Credentials <- v

    [<Parameter(Mandatory=false)>]
    member this.Option
        with get() = _Option
        and set(v) = _Option <- v

    override this.ProcessRecord() =
        let trust = new TrustAll()
        System.Net.ServicePointManager.set_CertificatePolicy( trust )
        let request = "https://" + this.Host + ":" + this.Port + "/services/search/jobs/export"
        let post = "?search=search " + this.SearchString + "&exec_mode=oneshot" + this.Option
        let request_post = request + post
        let splunk = new System.Net.WebClient()
        splunk.Credentials <- this.Credentials
        let page = splunk.DownloadString( request_post )
        this.WriteObject( page.ToString() )

