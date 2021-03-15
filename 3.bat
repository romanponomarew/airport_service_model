@echo off

set /a FLAG=1

:do
     python simulation.py %*
     python json_test.py
:while

     set %FLAG%=%FLAG% + 1
     if %FLAG% NEQ 10 (goto do) else (goto next)
:next

