@echo off
echo Starting Django App...

REM Activate virtual environment
call venv\Scripts\activate

REM Run migrations (optional)
python manage.py migrate

REM Run server
start http://127.0.0.1:8000
python manage.py runserver
