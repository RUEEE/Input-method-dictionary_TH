@echo off
setlocal EnableExtensions
set "CONVERTER=C:\disk\tools\__misc\深蓝词库转换\ImeWlConverterCmd.exe"
set "WIN10_SRC=C:\disk\tools\__misc\深蓝词库转换\Win10微软拼音词库.dat"
REM 深蓝会直接把dat生在自己的目录下，所以得复制一次

set "INPUT=.\mid\output_all.txt"
set "INPUT2=.\mid\output_nodup.txt"
set "INPUT3=.\mid\output_ms.txt"
set "OUT_WIN10=.\release\thd_win10.dat"
set "OUT_RIME=.\release\thd_rime.dict.yaml"
set "OUT_SOUGOU=.\release\thd_sougou.txt"

set "RIME_HEADER1=name: thd"
set "RIME_HEADER2=version: \"2026-01-12\""
set "RIME_HEADER3=sort: by_weight"
set "RIME_HEADER4=..."

if not exist "%CONVERTER%" (
  echo [ERROR] Converter not found: %CONVERTER%
  exit /b 1
)

if not exist "%INPUT%" (
  echo [ERROR] Input not found: %INPUT%
  exit /b 1
)

"%CONVERTER%" -i:rime "%INPUT3%" -o:win10mspy "%OUT_WIN10%"
if errorlevel 1 (
  echo [ERROR] Convert to win10mspy failed.
  exit /b 1
)

(
  echo %RIME_HEADER1%
  echo %RIME_HEADER2%
  echo %RIME_HEADER3%
  echo %RIME_HEADER4%
  type "%INPUT%"
) > "%OUT_RIME%"

if not exist "%INPUT2%" (
  echo [ERROR] input not found: %INPUT2%
  exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass ^
  -Command "$t=Get-Content -Raw -Encoding UTF8 '%INPUT2%';" ^
          "[IO.File]::WriteAllText('%OUT_SOUGOU%',$t,[Text.Encoding]::GetEncoding('gb2312'))"
if errorlevel 1 (
  echo [ERROR] convert failed.
  exit /b 1
)

REM 搜狗首字符不能是数字或字母，滤掉
set "OUT_SOUGOU_TMP=%OUT_SOUGOU%.tmp"
findstr /R /V "^[0-9A-Za-z]" "%OUT_SOUGOU%" > "%OUT_SOUGOU_TMP%"
if errorlevel 1 (
  echo [ERROR] filter sougou failed.
  exit /b 1
)
move /Y "%OUT_SOUGOU_TMP%" "%OUT_SOUGOU%" >nul

if not exist "%WIN10_SRC%" (
  echo [ERROR] Win10 source dat not found: %WIN10_SRC%
  exit /b 1
)
copy /Y "%WIN10_SRC%" "%OUT_WIN10%" >nul
if errorlevel 1 (
  echo [ERROR] Copy win10 dat failed.
  exit /b 1
)

echo Done.
echo   Win10: %OUT_WIN10%
echo   Rime : %OUT_RIME%
echo   Sougou : %OUT_SOUGOU%
cmd /k
