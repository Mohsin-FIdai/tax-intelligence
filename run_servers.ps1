$Python = 'C:\Users\Mohsin\.gemini\antigravity\scratch\tax-intelligence\python_env\python.exe'
cd C:\Users\Mohsin\.gemini\antigravity\scratch\tax-intelligence

Write-Host "Starting FastAPI Backend..."
Start-Process -FilePath $Python -ArgumentList "-m uvicorn backend.main:app --host 0.0.0.0 --port 8000" -WindowStyle Hidden -RedirectStandardOutput "backend.log" -RedirectStandardError "backend_error.log"

Write-Host "Starting Streamlit Dashboard..."
Start-Process -FilePath $Python -ArgumentList "-m streamlit run app\streamlit_app.py --server.port 8501 --server.headless true" -WindowStyle Hidden -RedirectStandardOutput "frontend.log" -RedirectStandardError "frontend_error.log"

Write-Host "Servers started in background."
