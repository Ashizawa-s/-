Set ws = CreateObject("Wscript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
ws.CurrentDirectory = fso.GetParentFolderName(WScript.ScriptFullName)
ws.Run "powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File """ & ws.CurrentDirectory & "\update_and_launch.ps1""", 0, False

