@echo off
REM Staggered launch script for multiple instances to reduce lock contention

echo Starting 3 staggered production instances...
echo Each instance will process different app_id ranges to minimize conflicts

REM Instance 0: app_id range 1-60,000  
start "XML_Processor_0" cmd /k "cd /d %~dp0 && python production_processor.py --server localhost\SQLEXPRESS --database XmlConversionDB --workers 4 --batch-size 250 --app-id-start 1 --app-id-end 60000 --limit 1000"

echo Instance 0 started (app_id 1-60K)
timeout /t 30 /nobreak

REM Instance 1: app_id range 60001-120000
start "XML_Processor_1" cmd /k "cd /d %~dp0 && python production_processor.py --server localhost\SQLEXPRESS --database XmlConversionDB --workers 4 --batch-size 250 --app-id-start 60001 --app-id-end 120000 --limit 1000"

echo Instance 1 started (app_id 60K-120K)
timeout /t 30 /nobreak

REM Instance 2: app_id range 120001-180000
start "XML_Processor_2" cmd /k "cd /d %~dp0 && python production_processor.py --server localhost\SQLEXPRESS --database XmlConversionDB --workers 4 --batch-size 250 --app-id-start 120001 --app-id-end 180000 --limit 1000"

echo Instance 2 started (app_id 120K-180K)
echo All instances launched with 30-second stagger
echo Monitor performance in separate terminals

pause