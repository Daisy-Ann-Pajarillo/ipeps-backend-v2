@REM for windows or cmd. Type command: migrate.bat to migrate the changes data to your database
@echo off
set FLASK_APP=application.py
flask db migrate
flask db upgrade