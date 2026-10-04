@echo off
chcp 65001 >nul
"C:\Users\jr_ti\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" "%~dp0mapa_apuracao_al.py"
if errorlevel 1 (
  echo.
  echo Nao foi possivel atualizar o mapa. Confira a conexao com a internet e a disponibilidade do TSE.
) else (
  echo.
  echo Atualizado: "%~dp0mapa_apuracao_al_2026.html"
)
pause
