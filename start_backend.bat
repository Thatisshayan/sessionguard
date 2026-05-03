@echo off
cd /d C:\Projects\SessionGuard\sessionguard
set PYTHONPATH=C:\Projects\SessionGuard\sessionguard
C:\Users\Shaya\AppData\Local\Programs\Python\Python312\Scripts\uvicorn.exe backend.main:app --host 127.0.0.1 --port 8000 --reload
