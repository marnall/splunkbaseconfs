# Let's check for Python module install
$pythonExe = Get-Command python -ErrorAction SilentlyContinue

if ($pythonExe) {
  python "C:\Program Files\SplunkUniversalForwarder\etc\apps\TA_certificate_checker\bin\certificate_checker.py"
}
