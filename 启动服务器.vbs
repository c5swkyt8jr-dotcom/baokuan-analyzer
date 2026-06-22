' 爆款拆解机 - 启动服务器 (VBS)
' 双击此文件启动，CMD窗口不关服务就一直在线

Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")

' 获取脚本所在目录
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
backendDir = scriptDir & "\backend"
venvPython = backendDir & "\venv\Scripts\python.exe"

' 检查 venv 是否存在
If Not fso.FileExists(venvPython) Then
    MsgBox "虚拟环境未找到！请先运行: cd backend && python -m venv venv && venv\Scripts\pip install -r requirements.txt", 16, "错误"
    WScript.Quit 1
End If

' 在 backend 目录下启动服务器
shell.CurrentDirectory = backendDir
cmd = "cmd /k ""title 爆款拆解机 & echo ============================================ & echo   爆款拆解机 v1.0 & echo ============================================ & echo. & echo   服务地址: http://127.0.0.1:8000 & echo   前端页面: http://127.0.0.1:8000/static/index.html & echo. & echo   * 请勿关闭此窗口，关闭即停止服务 * & echo ============================================ & echo. & " & venvPython & " -m uvicorn main:app --host 0.0.0.0 --port 8000 --log-level info"" 
shell.Run cmd, 1, False
