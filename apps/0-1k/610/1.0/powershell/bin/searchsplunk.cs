// Copyright 2011 Michael Vierling

using System;
using System.Collections.Generic;
using System.Text;
using System.Net;
using System.Net.Security;
using System.Security;
using System.Security.Cryptography.X509Certificates;
using System.Management.Automation;

namespace SearchSplunk
{
    [Cmdlet(System.Management.Automation.VerbsCommon.Search,"Splunk")]
    public class MySplunkCmdlet : Cmdlet
    {
        // callback used to validate the certificate in an SSL conversation
        private static bool ValidateRemoteCertificate(
            object sender,
            X509Certificate certificate,
            X509Chain chain,
            SslPolicyErrors policyErrors
        )
        {
            return true;
        }

        private string _Port = "8089";
        private string _Host = "splunk.yellowpages.com";
        private string _SearchString = "";
        private NetworkCredential _Credentials = new System.Net.NetworkCredential("search_user", "password");
        private string _Option = "";

        [Parameter(Mandatory = true, Position = 0, ValueFromPipeline = true)]
        public string SearchString
        {
            get { return _SearchString; }
            set { _SearchString = value; }
        }

        [Parameter(Mandatory = false)]
        public string Port
        {
            get { return _Port; }
            set { _Port = value; }
        }

        [Parameter(Mandatory = false)]
        public string Host
        {
            get { return _Host; }
            set { _Host = value; }
        }

        [Parameter(Mandatory = false)]
        public NetworkCredential Credentials
        {
            get { return _Credentials; }
            set { _Credentials = value; }
        }

        [Parameter(Mandatory = false)]
        public string Option
        {
            get { return _Option; }
            set { _Option = value; }
        }

        protected override void ProcessRecord()
        {
            System.Net.ServicePointManager.ServerCertificateValidationCallback +=
                new RemoteCertificateValidationCallback(ValidateRemoteCertificate);
            var request = "https://" + this.Host + ':' + this.Port + "/services/search/jobs/export";
            var post = "?search=search " + this.SearchString + "&exec_mode=oneshot" + this.Option;
            var request_post = request + post;
            var splunk = new System.Net.WebClient();
            splunk.Credentials = this.Credentials;
            var page = splunk.DownloadString( request_post );
            WriteObject(page);
        }
    }
}


