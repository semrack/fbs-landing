@echo off
rem Еженедельные отчёты semrack.ru: поисковые данные, аудит сайта, раз в месяц — Вордстат.
rem Результат: reports\ГГГГ-ММ-ДД\ и копии последних отчётов в reports\latest-*.html
chcp 65001 >nul
set PYTHONUTF8=1
set PY="D:\Program Files\python\python.exe"
cd /d "%~dp0.."
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd"') do set D=%%i
for /f %%i in ('powershell -NoProfile -Command "(Get-Date).Day"') do set DAY=%%i
set R=reports\%D%
if not exist "%R%" mkdir "%R%"
echo === %D% === > "%R%\log.txt"
git pull -q >> "%R%\log.txt" 2>&1
%PY% _tools\search_data.py --out "%R%\search-report" >> "%R%\log.txt" 2>&1
%PY% _tools\audit.py https://semrack.ru --out "%R%\audit-report" >> "%R%\log.txt" 2>&1
if %DAY% LEQ 7 (
  set WORDSTAT_OUT=%R%\wordstat-report
  %PY% _tools\wordstat.py >> "%R%\log.txt" 2>&1
  copy /y "%R%\wordstat-report.html" "reports\latest-wordstat.html" >nul 2>&1
)
copy /y "%R%\search-report.html" "reports\latest-search.html" >nul 2>&1
copy /y "%R%\audit-report.html" "reports\latest-audit.html" >nul 2>&1
echo Готово: %R%
