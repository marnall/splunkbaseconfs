rem Load SMF data to Splunk
cd C:\Users\ed_ru\zMetricsDb2\
set CLASSPATH=C:\Users\ed_ru\zMetricsDb2\Db2zMetrics.jar:.
echo %CLASSPATH%
cls
java -Xdiag  -Xmx2048M -jar zMetricsDb2.jar -input_filename C:\Users\ed_ru\DB2.SMF01132023.TRS -trace fine


