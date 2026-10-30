@echo off
REM Ollama serve autostart
REM 由 Windows 任务计划程序在用户登录时调用
set OLLAMA_MODELS=d:\trae项目2\ollama\models
set OLLAMA_MODEL_SERVER=https://mirror.ollama.com
"%LOCALAPPDATA%\Programs\Ollama\ollama.exe" serve
