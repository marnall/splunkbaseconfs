$source = Get-CimInstance -Class Win32_Product  -Filter "Name='UniversalForwarder'" | select -ExpandProperty InstallLocation
$sourcePath = [System.IO.Path]::GetDirectoryName($source)

$dest = Split-Path $sourcePath
$backupDir = '\splunkforwarderbackup\'

$destinationPath = $dest+$backupDir
$files = Get-ChildItem -Path $sourcePath -Recurse
$filecount = $files.count

$splunkInstaller = 'splunkforwarder-8.0.4-767223ac207f-x64-release.msi'
$splunkDir = 'etc\apps\uf_win_upgrade\static\'
$splunkInstallerDir = $source+$splunkDir
$logFile = '\upgrade.log'
$logDir = $dest+$logFile

$i=0


Foreach ($file in $files) {
    $i++
    Write-Progress -activity "Creating backup..." -status "($i of $filecount) $file" -percentcomplete (($i/$filecount)*100)
  
    # Determine the absolute path of this object's parent container.  This is stored as a different attribute on file and folder objects so we use an if block to cater for both
    if ($file.psiscontainer) {$sourcefilecontainer = $file.parent} else {$sourcefilecontainer = $file.directory}
 
    # Calculate the path of the parent folder relative to the source folder
    $relativepath = $sourcefilecontainer.fullname.SubString($sourcepath.length)
 
    # Copy the object to the appropriate folder within the destination folder
    copy-Item $file.fullname ($destinationPath + $relativepath)
}

Start-Process $splunkInstallerDir$splunkInstaller `
    –Wait  -Verbose –ArgumentList `
        "AGREETOLICENSE=`"Yes`"", `
        #"LOGON_USERNAME=`"Domain\splunksvc`"", `
        #"LOGON_PASSWORD=`"splunksvc@123`"", `
        #“DEPLOYMENT_SERVER=`”SPLUNKDEPLOY:8089`”” , `
        "/Liwem!", "$logDir" , /quiet

