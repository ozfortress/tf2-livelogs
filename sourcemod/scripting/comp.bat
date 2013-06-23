set sourceFile=%1
copy /A %sourceFile%.sp C:\Users\irok\Documents\Sourcemod\scripting\%sourceFile%.sp /A /Y
spcomp.exe %sourceFile%.sp -o../plugins/%sourceFile%.smx
::copy /B ..\plugins\%sourceFile%.smx E:\HLDS\orangebox\tf\addons\sourcemod\plugins\%sourceFile%.smx /B /Y
copy /B ..\plugins\%sourceFile%.smx E:\Dropbox\Public\%sourceFile%.smx /B /Y