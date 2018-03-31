@echo off

goto :main

:stop
chcp 866 >nul
set code=%1
if %code% gtr 0 echo Command #%code% failed!
exit %code%

:main
chcp 65001 >nul

