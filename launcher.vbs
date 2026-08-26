Set ws = CreateObject("Wscript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
ws.CurrentDirectory = fso.GetParentFolderName(WScript.ScriptFullName)
result = ws.Run("powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File """ & ws.CurrentDirectory & "\update_and_launch.ps1""", 0, True)
If result <> 0 Then
    logPath = ws.CurrentDirectory & "\startup_error.txt"
    message = "Startup failed."
    If fso.FileExists(logPath) Then
        Set logFile = fso.OpenTextFile(logPath, 1)
        message = message & vbCrLf & vbCrLf & logFile.ReadAll
        logFile.Close
    End If
    MsgBox message, 16, "Transcription System"
End If

