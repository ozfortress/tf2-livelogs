set sourceFile=%1
spcomp.exe %sourceFile%.sp -o../plugins/%sourceFile%.smx
copy /B ..\plugins\compiled\%sourceFile%.smx E:\HLDS\orangebox\tf\addons\sourcemod\plugins\%sourceFile%.smx /B /Y