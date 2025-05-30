@echo off
setlocal enabledelayedexpansion

REM Define ESC character
for /F "tokens=1 delims=#" %%a in ('"prompt #$E# & echo on & for %%b in (1) do rem"') do set "ESC=%%a"

REM Define some colors
set BLUE_COLOR=%ESC%[0;34m
set GREEN_COLOR=%ESC%[0;32m
set YELLOW_COLOR=%ESC%[0;33m
set RED_COLOR=%ESC%[0;31m
set NC=%ESC%[0m

echo %BLUE_COLOR%Aurite Agents Setup Script (Windows)%NC%
echo %BLUE_COLOR%====================================%NC%

REM Check for Docker and Docker Compose
echo.
echo %YELLOW_COLOR%Checking prerequisites...%NC%
docker --version >nul 2>&1
if errorlevel 1 (
    echo %RED_COLOR%ERROR: Docker CLI could not be found. Please install Docker.%NC%
    goto :eof
)
docker ps >nul 2>&1
if errorlevel 1 (
    echo %RED_COLOR%ERROR: Docker daemon is not responding. Please ensure Docker Desktop is running.%NC%
    goto :eof
)
docker compose version >nul 2>&1
if errorlevel 1 (
    docker-compose version >nul 2>&1
    if errorlevel 1 (
        echo %RED_COLOR%ERROR: Docker Compose ^(V2 plugin or standalone^) could not be found. Please install Docker Compose.%NC%
        goto :eof
    ) else (
        set DOCKER_COMPOSE_CMD=docker-compose
    )
) else (
    set DOCKER_COMPOSE_CMD=docker compose
)
echo %GREEN_COLOR%Docker daemon responding and Docker Compose found.%NC%

REM Handle .env file
echo.
echo %YELLOW_COLOR%Configuring .env file...%NC%
set ENV_FILE=.env
set ENV_EXAMPLE_FILE=.env.example
set NEW_API_KEY_VALUE=

if exist "%ENV_FILE%" (
    echo %YELLOW_COLOR%WARNING: An existing '%ENV_FILE%' file was found.%NC%
    set /p confirm_replace="Do you want to replace it with values from '%ENV_EXAMPLE_FILE%' and user inputs? (Y/n): "
    if /i "%confirm_replace:~0,1%"=="n" (
        echo Skipping .env file modification.
    ) else (
        echo Backing up existing .env to .env.bak
        if exist "%ENV_FILE%.bak" del "%ENV_FILE%.bak"
        ren "%ENV_FILE%" ".env.bak"
        copy "%ENV_EXAMPLE_FILE%" "%ENV_FILE%" >nul
        echo "'%ENV_FILE%' has been replaced with '%ENV_EXAMPLE_FILE%'.
        call :configure_env_vars
    )
) else (
    copy "%ENV_EXAMPLE_FILE%" "%ENV_FILE%" >nul
    echo "'%ENV_EXAMPLE_FILE%' copied to '%ENV_FILE%'.
    call :configure_env_vars
)
goto :after_env_config

:configure_env_vars
    set /p anthropic_key="Enter your ANTHROPIC_API_KEY: "
    if defined anthropic_key (
        powershell -Command "(Get-Content %ENV_FILE%) -replace '^ANTHROPIC_API_KEY=.*', 'ANTHROPIC_API_KEY=%anthropic_key%' | Set-Content %ENV_FILE%"
        echo %GREEN_COLOR%ANTHROPIC_API_KEY updated in '%ENV_FILE%'.%NC%
    ) else (
        echo Skipping ANTHROPIC_API_KEY update ^(no value provided^).
    )

    echo Generating a new local API_KEY...
    REM Basic random key for batch - PowerShell offers better random generation
    set "chars=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    set "NEW_API_KEY_VALUE="
    for /L %%N in (1,1,32) do (
        set /A "rand_num=!RANDOM! %% 62"
        for %%I in (!rand_num!) do set "NEW_API_KEY_VALUE=!NEW_API_KEY_VALUE!!chars:~%%I,1!"
    )
    powershell -Command "(Get-Content %ENV_FILE%) -replace '^API_KEY=.*', 'API_KEY=%NEW_API_KEY_VALUE%' | Set-Content %ENV_FILE%"
    echo %GREEN_COLOR%API_KEY updated in '%ENV_FILE%'.%NC%
    echo Your new API_KEY for the frontend UI is: %GREEN_COLOR%%NEW_API_KEY_VALUE%%NC%
    echo %YELLOW_COLOR%Please copy this key. You will need it to authenticate with the API via the UI.%NC%

    @REM set desired_project_config_path=
    @REM set /p desired_project_config_path="Enter desired PROJECT_CONFIG_PATH (e.g., config/projects/default.json) or press Enter to keep default: "
    @REM if defined desired_project_config_path (
    @REM     REM Ensure forward slashes for consistency if user uses backslashes
    @REM     set "desired_project_config_path=!desired_project_config_path:\=/!"
    @REM     powershell -Command "(Get-Content %ENV_FILE%) -replace '^PROJECT_CONFIG_PATH=.*', 'PROJECT_CONFIG_PATH=!desired_project_config_path!' ^| Set-Content %ENV_FILE%"
    @REM     if errorlevel 1 (
    @REM         echo %RED_COLOR%ERROR: Failed to update PROJECT_CONFIG_PATH in %ENV_FILE%.%NC%
    @REM     ) else (
    @REM         echo %GREEN_COLOR%PROJECT_CONFIG_PATH updated to '!desired_project_config_path!' in '%ENV_FILE%'.%NC%
    @REM     )
    @REM ) else (
    @REM     echo Skipping PROJECT_CONFIG_PATH update (no value provided).
    @REM )
    echo %GREEN_COLOR%Note: For the backend Docker container to connect to the PostgreSQL Docker container, AURITE_DB_HOST in '.env' should be 'postgres' ^(which is the default from .env.example^).%NC%
goto :eof

:after_env_config
echo.
echo %GREEN_COLOR%Environment setup phase complete.%NC%

REM Run Docker Compose
echo.
echo %YELLOW_COLOR%Starting services with Docker Compose...%NC%
%DOCKER_COMPOSE_CMD% up --build --abort-on-container-exit --remove-orphans

if errorlevel 1 (
    echo %RED_COLOR%ERROR: Docker Compose failed to start services. Check the output above.%NC%
    goto :eof
)

echo.
echo %GREEN_COLOR%Services started successfully!%NC%
for /f "tokens=1,2 delims==" %%a in ('findstr /b /c:"PORT=" "%ENV_FILE%"') do if "%%a"=="PORT" set ENV_PORT=%%b
if not defined ENV_PORT set ENV_PORT=8000
echo Backend should be available at %BLUE_COLOR%http://localhost:%ENV_PORT%%NC%
echo Frontend should be available at %BLUE_COLOR%http://localhost:5173%NC%

if defined NEW_API_KEY_VALUE (
  echo.
  echo %YELLOW_COLOR%Remember your API Key for the frontend UI: %GREEN_COLOR%%NEW_API_KEY_VALUE%%NC%
)

endlocal
goto :eof
