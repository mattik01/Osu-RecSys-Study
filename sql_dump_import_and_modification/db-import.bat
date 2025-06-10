@echo off
SETLOCAL ENABLEDELAYEDEXPANSION

:: === Hardcoded folder to import SQL from ===
set "folder=C:\Users\glaes\Desktop\GitHub\Osu-RecSys-Study\Data\import\2025_05_01_performance_osu_top_10000"

:: === Normalize folder path and extract schema name ===
for %%F in ("%folder%") do (
    set "fullpath=%%~fF"
    set "schema=%%~nxF"
)

echo Schema name: !schema!
echo Full path: !fullpath!

:: === Ensure input folder exists ===
if not exist "!fullpath!\" (
    echo ❌ Folder does not exist: !fullpath!
    pause
    exit /b
)

:: === Prepare log file in same directory as this script ===
set "scriptDir=%~dp0"
set "logFile=%scriptDir%import_log.txt"

echo Logging to: "!logFile!"
echo Starting import at %DATE% %TIME% > "!logFile!"

:: === MySQL config ===
set "MYSQL=mysql"
set "USER=root"
set "DATABASE=!schema!"

:: Prompt for MySQL password
set /p MYSQL_PASSWORD="Enter MySQL password for user '!USER!': "

:: Prompt and run MySQL interactively (user types password manually):
echo Creating MySQL schema: %schema% >> "%logFile%"
(
    echo DROP DATABASE IF EXISTS %DATABASE%;
    echo CREATE DATABASE %DATABASE%;
) | %MYSQL% -u %USER% -p >> "%logFile%" 2>&1

:: === Count SQL files ===
set /a count=0
for %%f in ("!fullpath!\*.sql") do (
    set /a count+=1
)
echo Found !count! SQL files in folder. >> "!logFile!"

set /a i=0
for %%f in ("!fullpath!\*.sql") do (
    call :import_one "%%f"
)
goto :eof

:import_one
set /a i+=1
set "filepath=%~1"
set "filename=%~nx1"
set "filesize="
for %%A in ("%filepath%") do set "filesize=%%~zA"

echo Hi >> "!logFile!"
echo. >> "!logFile!"
echo Importing [%filename%] (!i! of !count!) into schema [!DATABASE!]... >> "!logFile!"
echo Importing [%filename%] (!i! of !count!) into schema [!DATABASE!]...
echo File size: !filesize! bytes >> "!logFile!"
echo File size: !filesize! bytes

pv "%filepath%" | !MYSQL! -u !USER! -p!MYSQL_PASSWORD! !DATABASE! >> "!logFile!" 2>&1

if !ERRORLEVEL! NEQ 0 (
    echo ❌ Error occurred while importing [%filename%]. Check the log for details. >> "!logFile!"
    echo ❌ Error occurred while importing [%filename%]. Check the log for details.
) else (
    echo ✅ Successfully imported [%filename%] >> "!logFile!"
    echo ✅ Successfully imported [%filename%]
)
exit /b


echo. >> "!logFile!"
echo ✅ All SQL files imported into [!DATABASE!] >> "!logFile!"
echo ✅ All SQL files imported into [!DATABASE!]

pause
