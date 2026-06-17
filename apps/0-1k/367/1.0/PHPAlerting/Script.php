#!/usr/bin/php
<?php
echo "\n\nStarting php script...\n";
if (count($argv) <> 9 ){
	echo "This Script Requires 9 arguments to run.\nExiting with status of 1.\n";
	exit(1);
}
require("/Applications/splunk/bin/scripts/HelperScripts/PHPMailer_v5.1/class.phpmailer.php");
require("/Applications/splunk/bin/scripts/HelperScripts/PHPMailer_v5.1/class.smtp.php");

function SFTPSender($FTPFile,$RemoteDir) {
	global $FTPFile;
	global $FileLocation;
	$sendftp = "scp ".$FTPFile." ftpuser@ftpsite.com:".$RemoteDir;
	echo $sendftp."\n";
	`$sendftp`;
}



function PreProcFile()
{
	//Set Script Master Variables
	global $myFile;
	global $fh;
	global $NumEvents;
	global $SearchTerms;
	global $FullyQualSearch;
	global $NameSavedSplunk;
	global $TriggerReason;
	global $URL;
	global $EmptyField;
	global $FileLocation;
	global $NumOfArgs;
	global $path;
	global $file;
	global $path_parts;
	global $ext;
	global $UnZipName;
	global $csvarray;
	global $rezip;

	fwrite($fh, "Checking Extentions");
	if($ext == 'gz')
	{
		$execute = "gunzip ".$FileLocation;
		`$execute`;
		$rezip='yes';
	}
	
	fwrite($fh, "Opening Results File");
	// Open the File.
	if (($handle = fopen($UnZipName, "r")) !== FALSE) {
		// Set the parent multidimensional array key to 0.
		$nn = 0;
		fwrite($fh, "Loading CSV values\n");
		while (($data = fgetcsv($handle, 4000, ",")) !== FALSE) {
			// Count the total keys in the row.
			$c = count($data);
			// Populate the multidimensional array.
			for ($x=0;$x<$c;$x++)
			{
				$csvarray[$nn][$x] = $data[$x];
			}
			$nn++;
		}
		// Close the File.
		fclose($handle);
	}
}

function MailSender($EmailAddys,$SubjectLine,$BodyContents)
{
	fwrite($fh, "Starting MailSender $EmailAddys, $SubjectLine, $BodyContents");
	//error_reporting(E_ALL);
	error_reporting(E_STRICT);
	
	date_default_timezone_set('America/Denver');
	
	$mail			 = new PHPMailer();

	//$body			 = file_get_contents('./HelperScripts/PHPMailer_v5.1/examples/contents.html');
	$body			 = $BodyContents;
	$body			 = eregi_replace("[\]",'',$body);

	$mail->IsSMTP(); // telling the class to use SMTP
	$mail->Host	   = "mailrelay.com"; 	   // SMTP server
	$mail->SMTPDebug  = 2;						   // enables SMTP debug information (for testing)
									   // 1 = errors and messages
									   // 2 = messages only

	$mail->SetFrom('splunk@healthtrans.com', 'Healthtrans Alerting');
	
	$mail->Subject	= "$SubjectLine";
	
	//$mail->AltBody	= "To view the message, please use an HTML compatible email viewer!"; // optional, comment out and test

	$mail->MsgHTML($body);

	print_r($EmailAddys);
	foreach ($EmailAddys as $addyvalue){
		$address = $addyvalue;
		$mail->AddAddress($address, "");
	}

	//$mail->AddAttachment("images/phpmailer.gif");	  // attachment

	if(!$mail->Send()) {
		echo "Mailer Error: " . $mail->ErrorInfo;
	} else {
		echo "Message sent!";
	}
}

function cleanup()
{
	global $UnZipName;
	global $rezip;
	global $fh;
	fwrite($fh, "Running Cleanup");
	if($rezip == 'yes')
	{
		$execute = "gzip ".$UnZipName;
		`$execute`;
	}
	fclose($fh);
}

/*~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
~~~~~~~~~~~~~~~~  Start Script ~~~~~~~~~~~~~~~~~~~~~~~
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~*/



//Set Script Master Variables
$rezip = 'no';
$myFile = "/Applications/splunk/bin/scripts/3pea_output.txt";
$fh = fopen($myFile, 'w');


//Load Arguments into Variables
$NumEvents = $argv[1];
$SearchTerms = $argv[2];
$FullyQualSearch = $argv[3];
$NameSavedSplunk = $argv[4];
$TriggerReason = $argv[5];
$URL = $argv[6];
$EmptyField = $argv[7];
$FileLocation = $argv[8];
if (file_exists($FileLocation)) {
	echo "\nThe file $FileLocation exists\n";
} else {
	echo "\nThe file $FileLocation does not exist\n";
	echo "\nExiting with error code of 5\n";
	exit(5);
}
$NumOfArgs= count($argv);
$path = dirname($FileLocation);
$file = basename($FileLocation);
$path_parts = pathinfo($file);
$ext = $path_parts['extension'];
$UnZipName = $path."/".$path_parts['filename'];
$fh = fopen($myFile, 'w');


// Write the Arguments into the "myFile" file listed above
fwrite($fh, "Number of Events: ".$NumEvents."\n");
fwrite($fh, "Search Terms: ".$SearchTerms."\n");
fwrite($fh, "Fully Qualified Search String: ".$FullyQualSearch."\n");
fwrite($fh, "Name of Saved Splunk: ".$NameSavedSplunk."\n");
fwrite($fh, "Trigger Reason: ".$TriggerReason."\n");
fwrite($fh, "URL: ".$URL."\n");
fwrite($fh, "EmptyField: ".$EmptyField."\n");
fwrite($fh, "File Location: ".$FileLocation."\n");
fwrite($fh, "File Name: ".$file."\n"."File Path: ".$path."\n");


fwrite($fh, "Starting ScreenOut Ecchos");
// Echo Var's to Screen Out
foreach ($argv as $v) {
	echo "Current Value of \$argv: $v.\n";
}
echo "Number of Arguments = "."$NumOfArgs"."\n";
echo "Unzipped Filename: $UnZipName";

fwrite($fh, "Running PreProcFile Function");
PreProcFile();

fwrite($fh, "Starting Array Functions");
foreach ($csvarray as $key1 => $csvvalue1 ) {
	fwrite($fh, "Current Loop".$key1."\n");
	if ($key1==0){
		echo "First Run Loop\n";
		echo "Finding Value Locations\n";
		
		$PEA_FaultCode_key = array_search("PEA_FaultCode",$csvarray[$key1],1);
		$PEA_LookUpTemplate_key = array_search("PEA_LookUpTemplate",$csvarray[$key1],1);
		$PEA_FTPorEMAIL_key = array_search("PEA_FTPorEMAIL",$csvarray[$key1],1);
		$PEA_EMAILAddys_key = array_search("PEA_EMAILAddys",$csvarray[$key1],1);
		$PEA_EMAILSubject_key = array_search("PEA_EMAILSubject",$csvarray[$key1],1);
		$PEA_EMAILHeaderTxt_key = array_search("PEA_EMAILHeaderTxt",$csvarray[$key1],1);
		$PEA_EMAILRequiredFields_key = array_search("PEA_EMAILRequiredFields",$csvarray[$key1],1);
		$PEA_EMAILFooterTxt_key = array_search("PEA_EMAILFooterTxt",$csvarray[$key1],1);
		$PEA_FTPFileName_key = array_search("PEA_FTPFileName",$csvarray[$key1],1);
		$PEA_FTPHeaderTxt_key = array_search("PEA_FTPHeaderTxt",$csvarray[$key1],1);
		$PEA_FTPRequiredFields_key = array_search("PEA_FTPRequiredFields",$csvarray[$key1],1);
		$PEA_FTPFootertxt_key = array_search("PEA_FTPFootertxt",$csvarray[$key1],1);
		$PEA_Pharmacy_key = array_search("PEA_Pharmacy",$csvarray[$key1],1);
		$PEA_PharmacyID_key = array_search("PEA_PharmacyID",$csvarray[$key1],1);
		$PEA_PharmacyIDQual_key = array_search("PEA_PharmacyIDQual",$csvarray[$key1],1);
		$PEA_Phone_key = array_search("PEA_Phone",$csvarray[$key1],1);
		$PEA_Address_key = array_search("PEA_Address",$csvarray[$key1],1);
		$PEA_City_key = array_search("PEA_City",$csvarray[$key1],1);
		$PEA_State_key = array_search("PEA_State",$csvarray[$key1],1);
		$PEA_Zip_key = array_search("PEA_Zip",$csvarray[$key1],1);
		$PEA_RxIDNumber_key = array_search("PEA_RxIDNumber",$csvarray[$key1],1);
		$PEA_TranAmount_key = array_search("PEA_TranAmount",$csvarray[$key1],1);
		$ADJ_RxNumber_key = array_search("ADJ_RxNumber",$csvarray[$key1],1);
		$ADJ_Date_key = array_search("ADJ_Date",$csvarray[$key1],1);
		$ADJ_TimeStamp_key = array_search("ADJ_TimeStamp",$csvarray[$key1],1);

	} else {
		echo "Exporting Results for array $key1: \n";
			$PostVar["PEA_FaultCode"] = $csvarray[$key1][$PEA_FaultCode_key];
			$PostVar["PEA_LookUpTemplate"] = $csvarray[$key1][$PEA_LookUpTemplate_key];
			$PostVar["PEA_FTPorEMAIL"] = $csvarray[$key1][$PEA_FTPorEMAIL_key];
			$PostVar["PEA_EMAILAddys"] = $csvarray[$key1][$PEA_EMAILAddys_key];
			$PostVar["PEA_EMAILSubject"] = $csvarray[$key1][$PEA_EMAILSubject_key];
			$PostVar["PEA_EMAILHeaderTxt"] = $csvarray[$key1][$PEA_EMAILHeaderTxt_key];
			$PostVar["PEA_EMAILRequiredFields"] = $csvarray[$key1][$PEA_EMAILRequiredFields_key];
			$PostVar["PEA_EMAILFooterTxt"] = $csvarray[$key1][$PEA_EMAILFooterTxt_key];
			$PostVar["PEA_FTPFileName"] = $csvarray[$key1][$PEA_FTPFileName_key];
			$PostVar["PEA_FTPHeaderTxt"] = $csvarray[$key1][$PEA_FTPHeaderTxt_key];
			$PostVar["PEA_FTPRequiredFields"] = $csvarray[$key1][$PEA_FTPRequiredFields_key];
			$PostVar["PEA_FTPFootertxt"] = $csvarray[$key1][$PEA_FTPFootertxt_key];
			$PostVar["PEA_Pharmacy"] = $csvarray[$key1][$PEA_Pharmacy_key];
			$PostVar["PEA_PharmacyID"] = $csvarray[$key1][$PEA_PharmacyID_key];
			$PostVar["PEA_PharmacyIDQual"] = $csvarray[$key1][$PEA_PharmacyIDQual_key];
			$PostVar["PEA_Phone"] = $csvarray[$key1][$PEA_Phone_key];
			$PostVar["PEA_Address"] = $csvarray[$key1][$PEA_Address_key];
			$PostVar["PEA_City"] = $csvarray[$key1][$PEA_City_key];
			$PostVar["PEA_State"] = $csvarray[$key1][$PEA_State_key];
			$PostVar["PEA_Zip"] = $csvarray[$key1][$PEA_Zip_key];
			$PostVar["PEA_RxIDNumber"] = $csvarray[$key1][$PEA_RxIDNumber_key];
			$PostVar["PEA_TranAmount"] = $csvarray[$key1][$PEA_TranAmount_key];
			$PostVar["ADJ_RxNumber"] = $csvarray[$key1][$ADJ_RxNumber_key];
			$PostVar["ADJ_Date"] = $csvarray[$key1][$ADJ_Date_key];
			$PostVar["ADJ_TimeStamp"] = $csvarray[$key1][$ADJ_TimeStamp_key];

			echo "Echo'n vars  for this set";

			echo 'Faultcode = '.$PostVar["PEA_FaultCode"]."\n";
			echo 'LookupTemplate = '.$PostVar["PEA_LookUpTemplate"]."\n";
			echo 'FTPorEMAIL = '.$PostVar["PEA_FTPorEMAIL"]."\n";
			echo 'Emailaddys = '.$PostVar["PEA_EMAILAddys"]."\n";
			echo 'Email Suject = '.$PostVar["PEA_EMAILSubject"]."\n";
			echo 'Email Header = '.$PostVar["PEA_EMAILHeaderTxt"]."\n";
			echo 'Email Required Fields = '.$PostVar["PEA_EMAILRequiredFields"]."\n";
			echo 'Email FooterTXT = '.$PostVar["PEA_EMAILFooterTxt"]."\n";
			echo 'FTPFilename = '.$PostVar["PEA_FTPFileName"]."\n";
			echo 'FTPHeaderTxt = '.$PostVar["PEA_FTPHeaderTxt"]."\n";
			echo 'FTPRequireFields = '.$PostVar["PEA_FTPRequiredFields"]."\n";
			echo 'PEAFTPFooter = '.$PostVar["PEA_FTPFootertxt"]."\n";
			echo 'PEA_Pharmacy = '.$PostVar["PEA_Pharmacy"]."\n";
			echo 'PEA_Pharmacy ID = '.$PostVar["PEA_PharmacyID"]."\n";
			echo 'PEAPPharmacy ID Qual = '.$PostVar["PEA_PharmacyIDQual"]."\n";
			echo 'PEA Phone = '.$PostVar["PEA_Phone"]."\n";
			echo 'PEA Address = '.$PostVar["PEA_Address"]."\n";
			echo 'PEA City = '.$PostVar["PEA_City"]."\n";
			echo 'PEA State = '.$PostVar["PEA_State"]."\n";
			echo 'PEA Zip = '.$PostVar["PEA_Zip"]."\n";
			echo 'PEA RXID = '.$PostVar["PEA_RxIDNumber"]."\n";
			echo 'PEA Trans Amount = '.$PostVar["PEA_TranAmount"]."\n";
			echo 'Adjudication RX Number = '.$PostVar["ADJ_RxNumber"]."\n";
			echo 'Adjudication Date = '.$PostVar["ADJ_Date"]."\n";
			echo 'Adjudication Date = '.$csvarray[$key1][23]."\n";
			echo 'Adjudication TimeStamp ='.$PostVar["ADJ_TimeStamp"]."\n";
			echo 'Adjudication TimeStamp ='.$csvarray[$key1][24]."\n";

			if ($PostVar["PEA_FTPorEMAIL"] == "EMAIL" || $PostVar["PEA_FTPorEMAIL"] == "BOTH")
			{	
				echo "FTPorEmail set to EMAIL or BOTH, starting email loop\n";
				$MidBody = explode("|",$PostVar["PEA_EMAILRequiredFields"]);
				print_r($MidBody);
				foreach($MidBody as $MidBodyKey => $MidBodyValue)
				{
					if($MidBodyValue=="rx"){
						$MidBody[$MidBodyKey] = "<tr><td>"."Rx Number:	"."</td><td>".$PostVar["ADJ_RxNumber"]."</td></tr>";
					}
					elseif($MidBodyValue=="date"){
						$MidBody[$MidBodyKey] = "<tr><td>"."Date/Timestamp:	:"."</td><td>".$PostVar["ADJ_Date"]."/".$PostVar["ADJ_TimeStamp"]."</td></tr>";
					}
					elseif($MidBodyValue=="tt"){
						$MidBody[$MidBodyKey] = "<tr><td>"."Transaction Type:	"."</td><td>".$PostVar["PEA_PharmacyIDQual"]."</td></tr>";
					}
					elseif($MidBodyValue=="ta"){
						$MidBody[$MidBodyKey] = "<tr><td>"."Transaction Amount:	"."</td><td>".$PostVar["PEA_TranAmount"]."</td></tr>";
					}
					elseif($MidBodyValue=="rxid"){
						$MidBody[$MidBodyKey] = "<tr><td>"."RxID (Cardholder ID):	"."</td><td>".$PostVar["PEA_RxIDNumber"]."</td></tr>";
					}
					elseif($MidBodyValue=="phid"){
						$MidBody[$MidBodyKey] = "<tr><td>"."PharmacyID:	"."</td><td>".$PostVar["PEA_PharmacyID"]."</td></tr>";
					}
					elseif($MidBodyValue=="prid"){
						$MidBody[$MidBodyKey] = "<tr><td>"."ProviderID (ID Type Cd):	"."</td><td>".$PostVar["PEA_PharmacyIDQual"]."</td></tr>";
					}
					elseif($MidBodyValue=="phname"){
						$MidBody[$MidBodyKey] = "<tr><td>"."Pharmacy Name:	"."</td><td>".$PostVar["PEA_Pharmacy"]."</td></tr>";
					}
					elseif($MidBodyValue=="phcity"){
						$MidBody[$MidBodyKey] = "<tr><td>"."Pharmacy City:	"."</td><td>".$PostVar["PEA_City"]."</td></tr>";
					}
					elseif($MidBodyValue=="phstate"){
						$MidBody[$MidBodyKey] = "<tr><td>"."Pharmacy State:	"."</td><td>".$PostVar["PEA_State"]."</td></tr>";
					}
					elseif($MidBodyValue=="phtele"){
						$MidBody[$MidBodyKey] = "<tr><td>"."Pharmacy Telephone:	"."</td><td>".$PostVar["PEA_Phone"]."</td></tr>";
					}
				}
				unset($MidBodyKey);
				unset($MidBodyValue);
				$CompleteMidBody="<br>";
				print_r($MidBody);
				foreach($MidBody as $MidBodyValue)
				{
					$CompleteMidBody .= $MidBodyValue;
				}
				unset($MidBody);
				unset($MidBodyValue);
				$BodyTogether='<br><table border="0">'.$CompleteMidBody.'</table><br>';
				$EmailAddys = explode("|",$PostVar["PEA_EMAILAddys"]);
				print_r($EmailAddys);
				if ($PostVar["PEA_EMAILFooterTxt"] == "NONE" || $PostVar["PEA_EMAILFooterTxt"] == "") {
					$FooterTxt="Sincerely,<br><br>HealthTrans";
				} else {
					$FooterTxt=$PostVar["PEA_EMAILFooterTxt"];
				}
				$ComposeEmailBody= $PostVar["PEA_EMAILHeaderTxt"]."\n".$BodyTogether."\n".$FooterTxt."\n";
				fwrite($fh, "Entering Mail Function");
				MailSender($EmailAddys,$PostVar["PEA_EMAILSubject"],$ComposeEmailBody);
			} 
			if ($PostVar["PEA_FTPorEMAIL"] == "FTP" || $PostVar["PEA_FTPorEMAIL"] == "BOTH"){	
				echo "\n\n\n Entering FTP Function.";
				fwrite($fh, "Entering FTP FUnction");
				$CreateFTPFile = "/Applications/splunk/bin/scripts/cardfundingerror".$PostVar["ADJ_RxNumber"].$PostVar["ADJ_Date"]."-".$PostVar["ADJ_TimeStamp"].".txt";
				$FTPFile = $CreateFTPFile;
				$ftphandle = fopen($FTPFile, 'w');
				$MidBody = explode("|",$PostVar["PEA_FTPRequiredFields"]);
				print_r($MidBody);
				foreach($MidBody as $MidBodyKey => $MidBodyValue)
				{
					if($MidBodyValue=="rx"){
						$MidBody[$MidBodyKey] = "Rx Number:	"."		".$PostVar["ADJ_RxNumber"]."\n";
					}
					elseif($MidBodyValue=="date"){
						$MidBody[$MidBodyKey] = "Date/Timestamp:	"."		".$PostVar["ADJ_Date"]."/".$PostVar["ADJ_TimeStamp"]."\n";
					}
					elseif($MidBodyValue=="tt"){
						$MidBody[$MidBodyKey] = "Transaction Type:	"."	".$PostVar["PEA_PharmacyIDQual"]."\n";
					}
					elseif($MidBodyValue=="ta"){
						$MidBody[$MidBodyKey] = "Transaction Amount:	"."	".$PostVar["PEA_TranAmount"]."\n";
					}
					elseif($MidBodyValue=="rxid"){
						$MidBody[$MidBodyKey] = "RxID (Cardholder ID):	"."	".$PostVar["PEA_RxIDNumber"]."\n";
					}
					elseif($MidBodyValue=="phid"){
						$MidBody[$MidBodyKey] = "PharmacyID:	"."		".$PostVar["PEA_PharmacyID"]."\n";
					}
					elseif($MidBodyValue=="prid"){
						$MidBody[$MidBodyKey] = "ProviderID (ID Type Cd):	"."".$PostVar["PEA_PharmacyIDQual"]."\n";
					}
					elseif($MidBodyValue=="phname"){
						$MidBody[$MidBodyKey] = "Pharmacy Name:	"."		".$PostVar["PEA_Pharmacy"]."\n";
					}
					elseif($MidBodyValue=="phcity"){
						$MidBody[$MidBodyKey] = "Pharmacy City:	"."		".$PostVar["PEA_City"]."\n";
					}
					elseif($MidBodyValue=="phstate"){
						$MidBody[$MidBodyKey] = "Pharmacy State:	"."		".$PostVar["PEA_State"]."\n";
					}
					elseif($MidBodyValue=="phtele"){
						$MidBody[$MidBodyKey] = "Pharmacy Telephone:	"."	".$PostVar["PEA_Phone"]."\n";
					}
				}
				unset($MidBodyKey);
				unset($MidBodyValue);
				$CompleteMidBody="\n";
				print_r($MidBody);
				foreach($MidBody as $MidBodyValue)
				{
					$CompleteMidBody .= $MidBodyValue;
				}
				unset($MidBody);
				unset($MidBodyValue);
				$BodyTogether=$CompleteMidBody;
				if ($PostVar["PEA_FTPFootertxt"] == "NONE" || $PostVar["PEA_FTPFootertxt"] == "") {
					$FooterTxt="Sincerely,\n\nHealthTrans";
				} else {
					$FooterTxt=$PostVar["PEA_FTPFootertxt"];
				}
				$ComposeFTPBody= $PostVar["PEA_FTPHeaderTxt"]."\n".$BodyTogether."\n".$FooterTxt."\n";
				fwrite($ftphandle, $ComposeFTPBody);
				fclose($ftphandle);
				$RemoteDir="/home/ftproot/peaftp/outgoing";
				echo "\n\n\n Trying to FTP the file. \n";
				SFTPSender($FTPFile,$RemoteDir);
				echo "Leaving FTP Functions \n";
				echo "Removing File: $FTPFile \n";
				unlink($FTPFile);
			}
			unset($PostVar);
	}
}


fwrite($fh, "Cleanup");

cleanup();
exit(0);
?>
