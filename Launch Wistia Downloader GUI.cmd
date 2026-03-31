@echo off
setlocal
set "APP_DIR=%~dp0"
set "APP_PATH=%APP_DIR%app.pyw"
set "PYTHONW_EXE=C:\Users\Amir Mansaray\AppData\Local\Python\pythoncore-3.14-64\pythonw.exe"
set "PYTHON_EXE=C:\Users\Amir Mansaray\AppData\Local\Python\pythoncore-3.14-64\python.exe"

if exist "%PYTHONW_EXE%" (
    start "" "%PYTHONW_EXE%" "%APP_PATH%"
) else (
    start "" "%PYTHON_EXE%" "%APP_PATH%"
)
