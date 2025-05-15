@echo off
setlocal enabledelayedexpansion

REM Define some colors (won't work in all Windows terminals, but good for those that support ANSI)
set BLUE_COLOR=\033[0;34m
set GREEN_COLOR=\033[0;32m
set YELLOW_COLOR=\033[0;33m
set RED_COLOR=\033[0;31m
set NC=\033[0m

echo %BLUE_COLOR%Aurite Agents Setup Script (Windows)%NC%
echo %BLUE_COLOR%====================================%NC%

REM Check for Docker and Docker Compose
echo.
echo %YELLOW_COLOR%Checking prerequisites...%NC%
docker --version >nul 2>&1
if errorlevel 1 (
    echo %RED_COLOR%ERROR: Docker could not be found. Please install Docker.%NC%
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
echo %GREEN_COLOR%Docker and Docker Compose found.%NC%

REM Handle .env file
echo.
echo %YELLOW_COLOR%Configuring .env file...%NC%
set ENV_FILE=.env
set ENV_EXAMPLE_FILE=.env.example
set NEW_API_KEY_VALUE=

if exist "%ENV_FILE%" (
    echo %YELLOW_COLOR%WARNING: An existing '%ENV_FILE%' file was found.%NC%
    set /p confirm_replace="Do you want to replace it with values from '%ENV_EXAMPLE_FILE%' and user inputs? (y/N): "
    if /i not "%confirm_replace%"=="y" (
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

    set CONFIG_PROJECTS_DIR=config\projects
    echo Available project configurations in '%CONFIG_PROJECTS_DIR%':
    set i=0
    setlocal enabledelayedexpansion
    for %%f in ("%CONFIG_PROJECTS_DIR%\*.json") do (
        echo   !i!) %%~nxf
        set "projects[!i!]=%%~nxf"
        set /a i+=1
    )
    if %i% equ 0 (
        echo No project JSON files found in %CONFIG_PROJECTS_DIR%.
    ) else (
        set /p project_choice="Select a project configuration by number (or press Enter to skip): "
        REM Basic number validation
        echo !project_choice! | findstr /r /c:"^[0-9][0-9]*$" >nul
        if errorlevel 1 (
            echo Skipping project configuration selection or invalid input.
        ) else (
            if !project_choice! LSS %i% (
                set "selected_project_file_name=!projects[%project_choice%]!"
                set "rel_project_config_path=config/projects/!selected_project_file_name!"
                powershell -Command "(Get-Content %ENV_FILE%) -replace '^PROJECT_CONFIG_PATH=.*', 'PROJECT_CONFIG_PATH=!rel_project_config_path!' | Set-Content %ENV_FILE%"
                echo PROJECT_CONFIG_PATH set to '!rel_project_config_path!' in '%ENV_FILE%'.
            ) else (
                echo Invalid selection. Skipping project configuration.
            )
        )
    )
    endlocal
    echo %GREEN_COLOR%Note: For the backend Docker container to connect to the PostgreSQL Docker container, AURITE_DB_HOST in '.env' should be 'postgres' ^(which is the default from .env.example^).%NC%
goto :eof

:after_env_config
echo.
echo %GREEN_COLOR%Environment setup phase complete.%NC%

REM Ask to install optional ML dependencies
echo.
echo %YELLOW_COLOR%Optional ML Dependencies...%NC%
set ML_REQUIREMENTS_FILE=ml_requirements.txt
if exist "%ML_REQUIREMENTS_FILE%" (
    set /p install_ml_deps="Some MCP servers require additional ML packages (e.g., sentence-transformers). Do you want to install them now from '%ML_REQUIREMENTS_FILE%'? (y/N): "
    if /i "%install_ml_deps%"=="y" (
        echo Installing ML dependencies from '%ML_REQUIREMENTS_FILE%'...
        python -m pip install -r "%ML_REQUIREMENTS_FILE%"
        if errorlevel 1 (
            echo %RED_COLOR%ERROR: Failed to install ML dependencies. Please check the output and try manually.%NC%
        ) else (
            echo %GREEN_COLOR%ML dependencies installed successfully.%NC%
        )
    ) else (
        echo Skipping installation of optional ML dependencies.
        echo If you need them later, you can install them with: pip install -e .[ml] or pip install -r %ML_REQUIREMENTS_FILE%
    )
) else (
    echo Optional ML requirements file '%ML_REQUIREMENTS_FILE%' not found. Skipping this step.
)

REM Run Docker Compose
echo.
echo %YELLOW_COLOR%Starting services with Docker Compose...%NC%
%DOCKER_COMPOSE_CMD% up -d --build

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
