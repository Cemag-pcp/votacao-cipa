@echo off
setlocal

set "EXIT_CODE=0"

set "PROJECT_DIR=%~dp0"
if "%PROJECT_DIR:~-1%"=="\" set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"

set "APP_DIR=%PROJECT_DIR%\Inicio-Validade"
set "VENV_DIR=%PROJECT_DIR%\venv"
set "VENV_PYTHON=%VENV_DIR%\Scripts\python.exe"
set "REQUIREMENTS_FILE=%PROJECT_DIR%\requirements.txt"
set "MENU_FILE=%APP_DIR%\menu.py"

echo.
set /p "SISTEMA_PASSWORD=Digite a senha do sistema (Enter para usar a padrao atual): "

echo Atualizando repositorio...
where git >nul 2>nul
if errorlevel 1 (
    echo Git nao encontrado no PATH. Pulando git pull.
) else (
    git -C "%PROJECT_DIR%" pull
    if errorlevel 1 (
        echo Falha ao executar git pull.
        set "EXIT_CODE=1"
        goto end
    )
)

if exist "%VENV_PYTHON%" goto run_menu

echo Ambiente virtual nao encontrado. Criando venv...
where py >nul 2>nul
if not errorlevel 1 (
    py -3.12 -m venv "%VENV_DIR%" >nul 2>nul
)

if not exist "%VENV_PYTHON%" (
    where python >nul 2>nul
    if errorlevel 1 (
        echo Python nao encontrado no PATH.
        set "EXIT_CODE=1"
        goto end
    )
    python -m venv "%VENV_DIR%"
)

if not exist "%VENV_PYTHON%" (
    echo Nao foi possivel criar o ambiente virtual.
    set "EXIT_CODE=1"
    goto end
)

echo Instalando bibliotecas...
"%VENV_PYTHON%" -m pip install --upgrade pip
if errorlevel 1 (
    echo Falha ao atualizar o pip.
    set "EXIT_CODE=1"
    goto end
)

"%VENV_PYTHON%" -m pip install -r "%REQUIREMENTS_FILE%"
if errorlevel 1 (
    echo Falha ao instalar as bibliotecas.
    set "EXIT_CODE=1"
    goto end
)

:run_menu
if not exist "%MENU_FILE%" (
    echo Arquivo menu.py nao encontrado em "%MENU_FILE%".
    set "EXIT_CODE=1"
    goto end
)

echo Iniciando menu...
"%VENV_PYTHON%" "%MENU_FILE%"
if errorlevel 1 (
    echo A execucao do menu terminou com erro.
    set "EXIT_CODE=1"
    goto end
)

:end
echo.
if "%EXIT_CODE%"=="0" (
    echo Processo finalizado.
) else (
    echo Processo finalizado com erro.
)
pause
endlocal
