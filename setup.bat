@echo off
setlocal EnableDelayedExpansion

echo ======================================================================
echo                  Developer AI Tools Setup (Windows)
echo ======================================================================
echo This setup configures AI developer tools (Claude Code, Cursor, Cline,
echo Google Antigravity, OpenAI Codex, Windsurf, GitHub Copilot, and Aider)
echo with unified coding rules, automated AST linting, an MCP server, and
echo 33 agent workflow skills.
echo.
echo Before any files are modified, you will see a plain-prose preview of
echo all planned actions and can approve, reject, or customize each one.
echo ======================================================================
echo.

set "SCRIPT_DIR=%~dp0"
set "CONFIGURATOR=%SCRIPT_DIR%scripts\configure.py"

:: Check for uv or Python
where uv >nul 2>&1
if %errorlevel% equ 0 (
    set "RUNNER=uv run --no-project python"
    for /f "tokens=*" %%v in ('uv --version 2^>^&1') do echo [OK] uv detected: %%v
) else (
    python --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo [!] ERROR: Neither uv nor Python 3 was found in your PATH.
        echo     Please install uv or Python 3.9+ to run setup and linter tools.
        pause
        exit /b 1
    )
    set "RUNNER=python"
    for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo [OK] Python detected: %%v
)

echo Repo directory: %SCRIPT_DIR%
echo.

echo Choose configuration mode:
echo   [1] Guided Interactive Setup (Recommended: choose tools, scope, and review plan)
echo   [2] Configure ALL AI Tools globally (previews plan before applying)
echo   [3] Configure Claude Code only globally (previews plan before applying)
echo.
choice /C 123 /M "Select option [1, 2, or 3, default 1]"
set "MODE_CHOICE=%errorlevel%"

if "%MODE_CHOICE%"=="1" (
    echo.
    call %RUNNER% "%CONFIGURATOR%"
)
if "%MODE_CHOICE%"=="2" (
    echo.
    call %RUNNER% "%CONFIGURATOR%" --tools all --scope global --action append
)
if "%MODE_CHOICE%"=="3" (
    echo.
    call %RUNNER% "%CONFIGURATOR%" --tools claude --scope global --action append
)

if %errorlevel% neq 0 (
    echo.
    echo [!] Configuration was cancelled or encountered an error.
    pause
    exit /b %errorlevel%
)

:: Check for optional vulture package
echo.
echo ----------------------------------------------------------------------
echo Optional Dependency: Vulture Dead Code Analyzer
echo ----------------------------------------------------------------------
echo Vulture statically scans Python code for unreferenced functions and dead
echo code. It is only required if you run full whole-repository audits (--level full).
echo.
choice /C YN /M "Install optional 'vulture' package? "
if not errorlevel 2 (
    where uv >nul 2>&1
    if %errorlevel% equ 0 (
        echo [+] Running: uv tool install vulture
        uv tool install vulture
    ) else (
        echo [+] Running: pip install vulture
        pip install vulture
    )
)

:: Global shortcuts in PATH
echo.
echo ----------------------------------------------------------------------
echo Optional Convenience: Global Terminal Shortcuts
echo ----------------------------------------------------------------------
echo Adding ai-dev-tools\bin to your User PATH lets you run shortcuts like
echo 'aitools', 'ailint', and 'aifix' directly from any terminal or PowerShell.
echo Target directory: %SCRIPT_DIR%bin
echo.
choice /C YN /M "Add ai-dev-tools\bin to your User PATH? "
if not errorlevel 2 (
    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
        "$binPath = '%SCRIPT_DIR%bin'.TrimEnd('\'); " ^
        "$userPath = [Environment]::GetEnvironmentVariable('Path', 'User'); " ^
        "$parts = if ($userPath) { $userPath.Split(';') } else { @() }; " ^
        "if ($parts -notcontains $binPath) { $newPath = (($parts + $binPath) -join ';').Trim(';'); [Environment]::SetEnvironmentVariable('Path', $newPath, 'User'); Write-Host '[OK] Added to User PATH!' } else { Write-Host '[OK] Already in User PATH.' }"
    echo [NOTE] Please restart active terminal sessions for the updated PATH to take effect.
)

echo.
echo Setup finished. Selected AI tools configured.
echo Tip: Install full CLI suite in your environment with: uv tool install .
echo.
pause
