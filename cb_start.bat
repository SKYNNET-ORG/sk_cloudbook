
echo off
:: Pulsando enter, se queda en modo 1, si pulsas otra tecla se cambia a modo discreto
set modo=1
set /p "modo=Bienvenido a Cloudbook, pulsa enter para continuar, cualquier otra tecla para modo discreto: "

:: A continuacion introduce las rutas correctas de tu programa (ojo, entre comillas dobles)
set ruta_deployer_launcher="C:\Users\jramosdi\Desktop\Juan\SkyNNet\sk_cloudbook\cloudbook_deployer"
set ruta_agent="C:\Users\jramosdi\Desktop\Juan\SkyNNet\sk_cloudbook\cloudbook_agent"
set ruta_maker="C:\Users\jramosdi\Desktop\Juan\SkyNNet\sk_cloudbook\cloudbook_maker2"

:: Info, a continuacion los valores de colores cantosos y discretos
set deployer_cantoso=c0
set launcher_cantoso=20
set agent_cantoso=60
set maker_cantoso=90

set deployer_discreto=0c
set launcher_discreto=02
set agent_discreto=06
set maker_discreto=09

:: Instrucciones de ejecucion que puede venir bien ver por defecto
set nl=^& echo.
set instrucciones_deployer=Bienvenido al deployer^
%nl%======================^
%nl%	Pendiente terminar instrucciones^
%nl%	py cloudbook_deployer.py

set instrucciones_launcher=Bienvenido al launcher^
%nl%======================^
%nl%	Pendiente terminar instrucciones^
%nl%	py cloudbook_launch.py

set instrucciones_agent=Bienvenido al agente^
%nl%====================^
%nl%	Pendiente terminar instrucciones^
%nl%	py gui.py

set instrucciones_maker=Bienvenido al maker^
%nl%===================^
%nl%	Pendiente terminar instrucciones^
%nl%	py cloudbook_maker.py


 
rem Arranco el deployer
if %modo%==1 (set color=%deployer_cantoso%) else (set color=%deployer_discreto%)
start "Cloudbook Deployer" cmd /k "color %color% & echo %instrucciones_deployer% & cd %ruta_deployer_launcher%" 

rem Arranco el launcher/run
if %modo%==1 (set color=%launcher_cantoso%) else (set color=%launcher_discreto%)
start "Cloudbook Launcher" cmd /k "color %color% & echo %instrucciones_launcher% & cd %ruta_deployer_launcher%"

rem Arranco el agente
if %modo%==1 (set color=%agent_cantoso%) else (set color=%agent_discreto%)
start "Cloudbook Agente" cmd /k "color %color% & echo %instrucciones_agent% & cd %ruta_agent%"

rem Arranco el maker
if %modo%==1 (set color=%maker_cantoso%) else (set color=%maker_discreto%)
start "Cloudbook Maker" cmd /k "color %color% & echo %instrucciones_maker% & cd %ruta_maker%"

rem Tareas pendientes (TODO): Poner instrucciones en el echo inicial, colocar en esquinas (https://ritchielawrence.github.io/cmdow/)