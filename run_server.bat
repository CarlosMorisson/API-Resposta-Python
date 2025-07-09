@echo off
ECHO =================================================================
ECHO  INICIANDO SERVIDOR - FORCANDO AMBIENTE VIRTUAL CORRETO...
ECHO =================================================================

REM Define o caminho exato para o Python do nosso ambiente virtual
SET PYTHON_EXE=E:\PythonProject\gemini-audio-python\venv\Scripts\python.exe

REM Executa o Uvicorn usando o Python correto
%PYTHON_EXE% -m uvicorn main:app --host 0.0.0.0 --port 3000

ECHO =================================================================
ECHO  Servidor encerrado.
ECHO =================================================================
pause