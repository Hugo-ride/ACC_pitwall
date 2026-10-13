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
    set /p OPEN=Ouvrir le dossier dist ? ^(o/n^) : 
    if /i "!OPEN!"=="o" explorer "dist"
) else (
    echo.
    echo [ERREUR] L'executable n'a pas ete cree.
    echo Verifie les erreurs PyInstaller au-dessus.
)

echo.
pause
