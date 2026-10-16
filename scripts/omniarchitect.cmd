@echo off
:: © OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。

REM OmniArchitect launcher — pins the project root so nothing depends on the
REM caller's working directory.
REM
REM   scripts\omniarchitect.cmd doctor
REM   scripts\omniarchitect.cmd demo --out out
REM   scripts\omniarchitect.cmd change --project projects\demo-120 "我不喜欢客厅的电视背景墙"

setlocal
set "PROJECT_ROOT=%~dp0.."
set "PACKAGE_PARENT=%~dp0..\.."
set "PYTHONPATH=%PACKAGE_PARENT%;%PROJECT_ROOT%"

set "PY=%OMNIARCHITECT_PYTHON%"
if "%PY%"=="" set "PY=%USERPROFILE%\.workbuddy\binaries\python\envs\default\Scripts\python.exe"
if not exist "%PY%" set "PY=python"

pushd "%PROJECT_ROOT%"
"%PY%" -m omniarchitect %*
set "RC=%ERRORLEVEL%"
popd
exit /b %RC%

:: ---
:: © OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
