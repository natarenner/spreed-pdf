#!/bin/bash
#
# Setup script for Lead Export Cronjob
# This script configures the daily CSV export of non-converted leads
#
# Usage: sudo bash scripts/setup_cronjob.sh
#

set -e

echo "🚀 Configurando cronjob de exportação de leads..."

# Get the current user (who will own the cron job)
CURRENT_USER=${SUDO_USER:-$USER}
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="/var/log/spreed"

echo "📁 Diretório do projeto: $PROJECT_DIR"
echo "👤 Usuário: $CURRENT_USER"

# 1. Create log directory
echo ""
echo "📝 Criando diretório de logs..."
mkdir -p "$LOG_DIR"
chown $CURRENT_USER:$CURRENT_USER "$LOG_DIR"
echo "✅ Diretório criado: $LOG_DIR"

# 2. Create exports directory if it doesn't exist
echo ""
echo "📂 Verificando diretório de exports..."
mkdir -p "$PROJECT_DIR/exports"
touch "$PROJECT_DIR/exports/.gitkeep"
echo "✅ Diretório pronto: $PROJECT_DIR/exports"

# 3. Test the export script manually
echo ""
echo "🧪 Testando script de exportação..."
cd "$PROJECT_DIR"

# Try to check if container is running using docker compose
if ! docker compose ps | grep -q "api"; then
    echo "⚠️  Container API não está rodando. Pulando teste..."
    echo "   Execute 'docker compose up -d' antes de usar o cronjob."
else
    echo "Executando teste do script..."
    docker compose exec -T api sh -c "PYTHONPATH=. uv run python workers/export_leads.py"
    echo "✅ Teste concluído!"
fi

# Obter o caminho completo do executável docker
DOCKER_PATH=$(which docker)
if [ -z "$DOCKER_PATH" ]; then
    echo "❌ Erro: O comando 'docker' não foi encontrado no PATH. Certifique-se de que o Docker está instalado e acessível."
    exit 1
fi

# 4. Setup crontab
echo ""
echo "⏰ Configurando crontab..."

CRON_CMD="0 0 * * * cd $PROJECT_DIR && $DOCKER_PATH compose exec -T api sh -c 'PYTHONPATH=. uv run python workers/export_leads.py' >> $LOG_DIR/lead_export.log 2>&1"

# Check if cron job already exists
if sudo -u $CURRENT_USER crontab -l 2>/dev/null | grep -q "workers/export_leads.py"; then
    echo "⚠️  Cronjob já existe. Removendo versão antiga..."
    sudo -u $CURRENT_USER crontab -l 2>/dev/null | grep -v "workers/export_leads.py" | sudo -u $CURRENT_USER crontab -
fi

# Add new cron job
echo "Adicionando cronjob..."
(sudo -u $CURRENT_USER crontab -l 2>/dev/null; echo "$CRON_CMD") | sudo -u $CURRENT_USER crontab -

echo "✅ Cronjob instalado!"

# 5. Verify installation
echo ""
echo "🔍 Verificando instalação..."
echo "Cronjobs ativos para $CURRENT_USER:"
echo "----------------------------------------"
sudo -u $CURRENT_USER crontab -l | grep "export_leads.py" || echo "Nenhum cronjob encontrado"
echo "----------------------------------------"

# 6. Summary
echo ""
echo "✅ Configuração concluída!"
echo ""
echo "📊 Resumo:"
echo "  • Cronjob: Executará diariamente à meia-noite (00:00)"
echo "  • Logs: $LOG_DIR/lead_export.log"
echo "  • CSVs: $PROJECT_DIR/exports/"
echo ""
echo "🔧 Comandos úteis:"
echo "  • Ver logs:        tail -f $LOG_DIR/lead_export.log"
echo "  • Testar agora:    cd $PROJECT_DIR && docker compose exec api uv run python workers/export_leads.py"
echo "  • Ver CSVs:        ls -lh $PROJECT_DIR/exports/"
echo "  • Editar crontab:  crontab -e"
echo "  • Remover cronjob: crontab -e (e deletar a linha)"
echo ""
