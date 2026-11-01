$env:PYTHONPATH = Join-Path $PSScriptRoot '..\python_packages'
Set-Location -LiteralPath $PSScriptRoot
python -m streamlit run app.py --global.developmentMode false --server.address 127.0.0.1 --server.port 8502
