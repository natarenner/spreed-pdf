#!/bin/bash
set -e

# Função para criar um banco de dados se ele não existir
create_db_if_not_exists() {
    local db=$1
    echo "Verificando/Criando banco de dados: $db"
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "postgres" <<-EOSQL
        SELECT 'CREATE DATABASE $db'
        WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$db')\gexec
EOSQL
}

# Criar os bancos necessários
create_db_if_not_exists "pdf_api"
create_db_if_not_exists "formbricks"

echo "Bancos de dados configurados com sucesso!"
