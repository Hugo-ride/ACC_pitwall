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

REM Verification Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERREUR] Python n'est pas installe ou pas dans le PATH.
    echo Installe Python puis coche "Add Python to PATH".
    echo.
    pause
    exit /b 1
)

echo [1/4] Installation des dependances...
python -m pip install --upgrade pip >nul
python -m pip install --upgrade pyinstaller websockets pillow
if errorlevel 1 (
    echo.
    echo [ERREUR] Impossible d'installer les dependances.
    echo.
    pause
    exit /b 1
)

echo.
echo [2/4] Nettoyage des anciens builds...
if exist "dist\ACC_PitWall.exe" del /f /q "dist\ACC_PitWall.exe"
if exist "build" rmdir /s /q "build"

echo.
echo [3/4] Compilation PyInstaller...
python -m PyInstaller "ACC_PitWall.spec" --clean --noconfirm
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
if exist "dist\ACC_PitWall.exe" (
    echo.
    echo ==============================================
    echo   SUCCES !
    echo   Fichier : dist\ACC_PitWall.exe
    for %%A in ("dist\ACC_PitWall.exe") do echo   Taille  : %%~zA octets
    echo ==============================================
    echo.
    echo Pour distribuer : copier uniquement dist\ACC_PitWall.exe
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
