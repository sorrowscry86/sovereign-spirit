@echo off
TITLE VoidCat RDC - Sovereign Spirit Management Console
COLOR 0B

:MENU
CLS
ECHO ===============================================================================
ECHO   V O I D C A T   R D C   -   S O V E R E I G N   S P I R I T
ECHO ===============================================================================
ECHO.
ECHO   [1] START System (Docker Compose Up)
ECHO   [2] STOP System (Docker Compose Down)
ECHO   [3] VIEW LOGS (Middleware)
ECHO   [4] RESTART Middleware
ECHO   [5] OPEN DASHBOARD
ECHO.
ECHO   [0] EXIT
ECHO.
SET /P M=Type 1, 2, 3, 4, 5, or 0 then press ENTER: 

IF %M%==1 GOTO START
IF %M%==2 GOTO STOP
IF %M%==3 GOTO LOGS
IF %M%==4 GOTO RESTART
IF %M%==5 GOTO DASHBOARD
IF %M%==0 GOTO EOF

:START
ECHO Running Static Analysis (The Sentinel)...
python sentinel.py
IF %ERRORLEVEL% NEQ 0 (
    ECHO [ERROR] Static Analysis Failed. Aborting startup.
    PAUSE
    GOTO MENU
)
ECHO [PASS] Analysis Clear.
ECHO Starting System...
docker-compose up -d
ECHO System Started.
PAUSE
GOTO MENU

:STOP
ECHO Stopping System...
docker-compose down
ECHO System Stopped.
PAUSE
GOTO MENU

:LOGS
docker-compose logs -f middleware
GOTO MENU

:RESTART
ECHO Restarting Middleware...
docker-compose restart middleware
ECHO Middleware Restarted.
PAUSE
GOTO MENU

:DASHBOARD
start http://localhost:5173
GOTO MENU
