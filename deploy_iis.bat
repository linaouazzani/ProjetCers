@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1

set "PROJECT_DIR=C:\Users\HP\Documents\CERS\ProjetCers"
set "PYTHON=C:\Users\HP\AppData\Local\Programs\Python\Python311\python.exe"
set "TARGET_IP=10.12.16.17"
set "FLASK_URL=http://localhost:5000/ping"

echo ============================================================
echo   CERS -- Script de Deploiement IIS
echo   Projet : %PROJECT_DIR%
echo   IP cible : %TARGET_IP%
echo ============================================================
echo.

:: ── 1. Git add + commit ──────────────────────────────────────────
echo [1/4] Commit Git en cours...
cd /d "%PROJECT_DIR%"

git add .
if errorlevel 1 (
    echo ERREUR : git add a echoue.
    goto :error
)

for /f "tokens=1-3 delims=/ " %%a in ("%date%") do set "DATE_TAG=%%c-%%b-%%a"
for /f "tokens=1-2 delims=:." %%a in ("%time: =0%") do set "TIME_TAG=%%a%%b"

git commit -m "deploy: mise a jour deploiement IIS %DATE_TAG% %TIME_TAG%" 2>nul
if errorlevel 1 (
    echo INFO : Rien a commiter (working tree propre).
) else (
    echo OK : Commit effectue.
)
echo.

:: ── 2. Validation syntaxe Python ─────────────────────────────────
echo [2/4] Validation syntaxe Python...
"%PYTHON%" -m py_compile "%PROJECT_DIR%\api.py"
if errorlevel 1 (
    echo ERREUR : api.py contient des erreurs de syntaxe !
    goto :error
)
"%PYTHON%" -m py_compile "%PROJECT_DIR%\app.py"
if errorlevel 1 (
    echo ERREUR : app.py contient des erreurs de syntaxe !
    goto :error
)
echo OK : Syntaxe Python valide.
echo.

:: ── 3. Redemarrage IIS ───────────────────────────────────────────
echo [3/4] Redemarrage IIS...
iisreset /restart /timeout:30
if errorlevel 1 (
    echo AVERTISSEMENT : iisreset a renvoye une erreur.
    echo   Verifiez que ce script est lance en tant qu'administrateur.
) else (
    echo OK : IIS redémarre avec succes.
)
echo.

:: ── 4. Test de connectivite reseau ───────────────────────────────
echo [4/4] Test de connectivite reseau...
echo.

echo   Ping sur %TARGET_IP% ...
ping -n 3 -w 1000 %TARGET_IP% >nul 2>&1
if errorlevel 1 (
    echo   [ECHEC] Le serveur %TARGET_IP% ne repond pas au ping.
    echo   Verifiez l'adresse IP et la connexion reseau.
    echo   Si l'IP a change, mettre a jour lancer.md et ce script.
) else (
    echo   [OK] %TARGET_IP% repond au ping.
)
echo.

echo   Verification API Flask sur %FLASK_URL% ...
curl -s --max-time 5 "%FLASK_URL%" >nul 2>&1
if errorlevel 1 (
    echo   [ECHEC] L'API Flask ne repond pas sur le port 5000.
    echo   Lancer manuellement : %PYTHON% api.py
    echo   Ou verifier le service NSSM : nssm status CersFlaskAPI
) else (
    echo   [OK] API Flask operationnelle.
)
echo.

:: ── Resume ───────────────────────────────────────────────────────
echo ============================================================
echo   Deploiement termine.
echo   Frontend IIS : http://%TARGET_IP%/rapportcers/php
echo   API Flask    : http://localhost:5000/ping
echo ============================================================
echo.
goto :end

:error
echo.
echo ============================================================
echo   DEPLOIEMENT INTERROMPU -- Corriger l'erreur ci-dessus.
echo ============================================================
exit /b 1

:end
endlocal
pause
