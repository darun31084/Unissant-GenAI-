@echo off
echo Installing what the project needs (first time only)...
py -m pip install -r requirements.txt
echo.
echo Starting the website at http://localhost:8501 - leave this window open.
echo (Paste your AI key in the sidebar of the website, or put it in a .env file.)
py -m streamlit run app.py
pause
