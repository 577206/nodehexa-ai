@echo off
setlocal EnableExtensions

rem Build the application in apps from any working directory.
rem Optional: build.bat -pid <PID> -secret <SECRET>
set "ROOT_DIR=%~dp0"
if "%ROOT_DIR:~-1%"=="\" set "ROOT_DIR=%ROOT_DIR:~0,-1%"
set "ADF_PATH=%ROOT_DIR%"
set "IDF_PATH=%ROOT_DIR%\esp-idf"
set "APP_DIR=%ROOT_DIR%\apps"
set "FW_DIR=%ROOT_DIR%\firmware"
set "APP_BIN=vb701n.bin"
set "DEFAULT_CLOUD_PID=11753"
set "BUILD_EXIT_CODE="
set "MERGE_EXIT_CODE="
set "FLASH_MONITOR_EXIT_CODE="
set "EXIT_CODE="
set "CLOUD_PID="
set "CLOUD_SECERT="
set "NO_FLASH=0"

:parse_args
if "%~1"=="" goto :args_done
if /i "%~1"=="-pid" (
    if "%~2"=="" (
        echo ERROR: -pid requires a value
        exit /b 1
    )
    set "CLOUD_PID=%~2"
    shift
    shift
    goto :parse_args
)
if /i "%~1"=="-secret" (
    if "%~2"=="" (
        echo ERROR: -secret requires a value
        exit /b 1
    )
    set "CLOUD_SECERT=%~2"
    shift
    shift
    goto :parse_args
)
if /i "%~1"=="-noflesh" (
    set "NO_FLASH=1"
    shift
    goto :parse_args
)
if /i "%~1"=="-h" goto :usage
if /i "%~1"=="--help" goto :usage
if /i "%~1"=="/?" goto :usage
echo ERROR: Unknown argument: %~1
goto :usage

:args_done

if not exist "%ADF_PATH%\export.bat" (
    echo ERROR: Cannot find the repository export script: "%ADF_PATH%\export.bat"
    exit /b 1
)
if not exist "%APP_DIR%\CMakeLists.txt" (
    echo ERROR: Cannot find the apps project at "%APP_DIR%"
    exit /b 1
)
if not exist "%IDF_PATH%\tools\idf.py" (
    echo ERROR: ESP-IDF is not initialized at "%IDF_PATH%"
    echo Run install.bat first.
    exit /b 1
)
if not exist "%ROOT_DIR%\qumios-dev\components\qm_agent\include\qm_agent.h" (
    echo ERROR: qumios-dev is not initialized.
    echo Run install.bat first.
    exit /b 1
)

where.exe git.exe >nul 2>&1
if errorlevel 1 (
    echo ERROR: git.exe was not found in PATH.
    exit /b 1
)
python.exe --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: python.exe was not found in PATH.
    echo Run install.bat from a terminal with Python available.
    exit /b 1
)

echo.
echo [1/4] Exporting ESP-IDF and applying ADF patches...
call "%ADF_PATH%\export.bat"
if errorlevel 1 goto :failed
if not defined IDF_PYTHON_ENV_PATH (
    echo ERROR: ESP-IDF Python environment was not exported.
    echo Run install.bat again, then retry build.bat.
    set "BUILD_EXIT_CODE=1"
    goto :failed
)
set "IDF_PYTHON=%IDF_PYTHON_ENV_PATH%\Scripts\python.exe"
if not exist "%IDF_PYTHON%" (
    echo ERROR: ESP-IDF Python was not found: "%IDF_PYTHON%"
    echo Run install.bat again, then retry build.bat.
    set "BUILD_EXIT_CODE=1"
    goto :failed
)

rem Always pass both so a previous override does not stick in CMake cache.
set "CMAKE_CLOUD_DEFS=-DXJIANG_CLOUD_PID=%CLOUD_PID% -DXJIANG_CLOUD_SECERT=%CLOUD_SECERT%"
if not "%CLOUD_PID%"=="" (
    echo Cloud PID override: %CLOUD_PID%
) else (
    echo Cloud PID: header default
)
if not "%CLOUD_SECERT%"=="" (
    echo Cloud SECERT override: set
) else (
    echo Cloud SECERT: header default
)

echo.
echo [2/4] Building the apps project...
pushd "%APP_DIR%"
if errorlevel 1 goto :failed
"%IDF_PYTHON%" "%IDF_PATH%\tools\idf.py" %CMAKE_CLOUD_DEFS% build
set "BUILD_EXIT_CODE=%ERRORLEVEL%"
if not "%BUILD_EXIT_CODE%"=="0" (
    popd
    goto :failed
)
popd

rem Full flash image from flash_args (bootloader + table + app + ota + phy + model).
if not "%CLOUD_PID%"=="" (
    set "OUT_PID=%CLOUD_PID%"
) else (
    set "OUT_PID=%DEFAULT_CLOUD_PID%"
)
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMddHHmmss"') do set "FW_TS=%%i"
if not exist "%FW_DIR%" mkdir "%FW_DIR%"
if errorlevel 1 (
    echo ERROR: Cannot create firmware dir: "%FW_DIR%"
    set "MERGE_EXIT_CODE=1"
    goto :failed
)
rem Keep only one firmware: remove previous ljyd_esp32_devkit_*.bin before merge.
del /q "%FW_DIR%\ljyd_esp32_devkit_*.bin" >nul 2>&1
set "FW_NAME=ljyd_esp32_devkit_%OUT_PID%_%FW_TS%.bin"
set "FW_OUT=%FW_DIR%\%FW_NAME%"

echo.
echo [3/4] Merging full flash image to firmware...
if not exist "%APP_DIR%\build\%APP_BIN%" (
    echo ERROR: App binary not found: "%APP_DIR%\build\%APP_BIN%"
    set "MERGE_EXIT_CODE=1"
    goto :failed
)
if not exist "%APP_DIR%\build\flash_args" (
    echo ERROR: flash_args not found: "%APP_DIR%\build\flash_args"
    set "MERGE_EXIT_CODE=1"
    goto :failed
)
rem idf.py merge-bin feeds @flash_args which has --flash_size detect;
rem esptool merge_bin rejects "detect". Call esptool with 16MB explicitly.
pushd "%APP_DIR%\build"
if errorlevel 1 goto :failed
"%IDF_PYTHON%" -m esptool --chip esp32s3 merge_bin -o "%FW_OUT%" --flash_mode dio --flash_freq 80m --flash_size 16MB 0x0 bootloader/bootloader.bin 0x10000 partition_table/partition-table.bin 0x1d000 ota_data_initial.bin 0x1f000 phy_init_data.bin 0x20000 %APP_BIN% 0x810000 espdl_models/coco_pose.espdl
set "MERGE_EXIT_CODE=%ERRORLEVEL%"
popd
if not "%MERGE_EXIT_CODE%"=="0" goto :failed
if not exist "%FW_OUT%" (
    echo ERROR: Merged firmware was not created: "%FW_OUT%"
    set "MERGE_EXIT_CODE=1"
    goto :failed
)
echo Full image: "%FW_OUT%"
echo FIRMWARE_OK=%FW_OUT%

if "%NO_FLASH%"=="1" (
    echo.
    echo Build and merge completed successfully. Flash skipped [-noflesh].
    echo Build dir: "%APP_DIR%\build"
    echo Firmware:  "%FW_OUT%"
    endlocal
    exit /b 0
)

echo.
echo [4/4] Flashing the application and starting the serial monitor...
pushd "%APP_DIR%"
if errorlevel 1 goto :failed
"%IDF_PYTHON%" "%IDF_PATH%\tools\idf.py" flash monitor
set "FLASH_MONITOR_EXIT_CODE=%ERRORLEVEL%"
popd
if not "%FLASH_MONITOR_EXIT_CODE%"=="0" (
    goto :failed
)

echo.
echo Build, flash, and monitor completed successfully.
echo Build dir: "%APP_DIR%\build"
echo Firmware:  "%FW_OUT%"
echo FIRMWARE_OK=%FW_OUT%
endlocal
exit /b 0

:usage
echo.
echo Usage: build.bat [-pid PID] [-secret SECRET] [-noflesh]
echo   -pid      Override CONFIG_XJIANG_CLOUD_PID
echo   -secret   Override CONFIG_XJIANG_CLOUD_SECERT
echo   -noflesh  Build and merge only; skip flash/monitor [for server]
echo   Omit pid/secret to use defaults in apps\main\cloud\ljyd_cloud.h
echo.
echo After a successful build, a full flash image is written to:
echo   firmware\ljyd_esp32_devkit_^<PID^>_^<yyyyMMddHHmmss^>.bin
echo On success the script prints FIRMWARE_OK=^<absolute path^> and exits 0.
echo.
echo Example:
echo   build.bat -pid 11753 -secret C9CEE6A076384D86B06FAE52C48EBE11
echo   build.bat -pid 11753 -secret C9CEE6A076384D86B06FAE52C48EBE11 -noflesh
endlocal
exit /b 1

:failed
if defined FLASH_MONITOR_EXIT_CODE (
    set "EXIT_CODE=%FLASH_MONITOR_EXIT_CODE%"
) else if defined MERGE_EXIT_CODE (
    set "EXIT_CODE=%MERGE_EXIT_CODE%"
) else if defined BUILD_EXIT_CODE (
    set "EXIT_CODE=%BUILD_EXIT_CODE%"
) else (
    set "EXIT_CODE=%ERRORLEVEL%"
)
if "%EXIT_CODE%"=="0" set "EXIT_CODE=1"
echo.
echo Build failed with exit code %EXIT_CODE%.
endlocal & exit /b %EXIT_CODE%
