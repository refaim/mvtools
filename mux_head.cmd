@echo off

goto :main

:stop
chcp 866 >nul
set code=%1
if [%code%] equ [] set code=1
exit %code%

:main
chcp 65001 >nul

