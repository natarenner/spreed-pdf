#!/bin/bash
# 
# Script executado pelo Cron para exportar leads
#

PROJECT_DIR="/root/spreed-pdf"
LOG_FILE="$PROJECT_DIR/exports/lead_export.log"

echo "--- [$(date)] Iniciando execução automática ---" >> "$LOG_FILE"

# Entrar no diretório
cd "$PROJECT_DIR" || { echo "ERRO: Não conseguiu entrar em $PROJECT_DIR" >> "$LOG_FILE"; exit 1; }

# Executar o docker 
# Usamos o caminho absoluto e garantimos o PYTHONPATH
/usr/bin/docker compose exec -T api sh -c "PYTHONPATH=. uv run python workers/export_leads.py" >> "$LOG_FILE" 2>&1

echo "--- [$(date)] Execução finalizada ---" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"
