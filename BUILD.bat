@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul
title ACC Pit Wall - Compilation

echo.
echo ==============================================
echo   ACC PIT WALL - Compilation en .exe
echo ==============================================
echo.

REM Se placer automatiquement dans le dossier du fichier BUILD.bat
cd /d "%~dp0"

set "APP_NAME=ACC_PitWall"
set "DEV_BUILD=0"
set "BUILD_INSTALLER=0"
if /i "%~1"=="dev" (
    set "APP_NAME=ACC_PitWall_Dev"
    set "DEV_BUILD=1"
    if not exist "ACC_pitwall_donnees\*.json" (
        echo [ERREUR] Les donnees de developpement sont absentes.
        echo Place les fichiers JSON dans ACC_pitwall_donnees puis relance BUILD.bat dev.
        echo.
        pause
        exit /b 1
    )
)
if /i "%~1"=="installer" set "BUILD_INSTALLER=1"

set "PYTHON=%~dp0.venv\Scripts\python.exe"
if not exist "%PYTHON%" (
    python --version >nul 2>&1
    if errorlevel 1 (
        echo [ERREUR] Python n'est pas installe ou pas dans le PATH.
        echo Installe Python 3.10 ou plus recent puis coche "Add Python to PATH".
        echo.
        pause
        exit /b 1
    )

    echo Creation de l'environnement de compilation...
    python -m venv "%~dp0.venv"
    if errorlevel 1 (
        echo [ERREUR] Impossible de creer l'environnement Python.
        echo.
        pause
        exit /b 1
    )
)

echo [1/4] Installation des dependances...
"%PYTHON%" -m pip install pyinstaller websockets pywebview
if errorlevel 1 (
    echo.
    echo [ERREUR] Impossible d'installer les dependances.
    echo.
    pause
    exit /b 1
)
for /f "tokens=2 delims== " %%V in ('findstr /b "APP_VERSION" version.py') do set "ACC_PITWALL_VERSION=%%~V"
if not defined ACC_PITWALL_VERSION (
    echo [ERREUR] Impossible de lire la version depuis version.py.
    pause
    exit /b 1
)

echo.
echo [2/4] Nettoyage des anciens builds...
if exist "dist\%APP_NAME%.exe" del /f /q "dist\%APP_NAME%.exe"
if exist "build" rmdir /s /q "build"

echo.
echo [3/4] Compilation PyInstaller...
set "ACC_PITWALL_DEV_BUILD=%DEV_BUILD%"
"%PYTHON%" -m PyInstaller "ACC_PitWall.spec" --clean --noconfirm
set "ACC_PITWALL_DEV_BUILD="
if errorlevel 1 (
    echo.
    echo [ERREUR] La compilation a echoue.
    echo Lis les lignes d'erreur juste au-dessus.
    echo.
    pause
    exit /b 1
)

if "%BUILD_INSTALLER%"=="1" (
    echo.
    echo [4/5] Creation de l'installateur...
    set "ISCC="
    for %%I in (ISCC.exe) do set "ISCC=%%~$PATH:I"
    if not defined ISCC if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
    if not defined ISCC if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
    if not defined ISCC if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
    if not defined ISCC (
        echo [ERREUR] Inno Setup 6 est requis pour creer l'installateur.
        echo Installe Inno Setup depuis https://jrsoftware.org/isinfo.php puis relance BUILD.bat installer.
        pause
        exit /b 1
    )
    "!ISCC!" "/DAppVersion=%ACC_PITWALL_VERSION%" "installer\ACC_PitWall.iss"
    if errorlevel 1 (
        echo [ERREUR] La creation de l'installateur a echoue.
        pause
        exit /b 1
    )
)

echo.
echo [4/4] Verification...
if exist "dist\%APP_NAME%.exe" (
    echo.
    echo ==============================================
    echo   SUCCES !
    echo   Fichier : dist\%APP_NAME%.exe
    for %%A in ("dist\%APP_NAME%.exe") do echo   Taille  : %%~zA octets
    echo ==============================================
    echo.
    echo   Pour utiliser : lancer directement dist\%APP_NAME%.exe
    echo.
    if "%BUILD_INSTALLER%"=="1" echo   Installateur : dist\ACC_PitWall_Setup_v%ACC_PITWALL_VERSION%.exe
    set /p OPEN=Ouvrir le dossier dist ? ^(o/n^) : 
    if /i "!OPEN!"=="o" explorer "dist"
) else (
    echo.
    echo [ERREUR] L'executable n'a pas ete cree.
    echo Verifie les erreurs PyInstaller au-dessus.
    exit /b 1
)

echo.
pause
