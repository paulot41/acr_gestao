#!/bin/bash
set -e

echo "=== Configuração de SSL com Let's Encrypt ==="

DOMAINS="acrsantatecla.duckdns.org proformsc.duckdns.org"
EMAIL="your-email@example.com"  # Altere para seu email

# Criar diretórios necessários
mkdir -p certbot/conf certbot/www ssl

# Gerar certificado autoassinado temporário para desenvolvimento
if [ ! -f "ssl/nginx-selfsigned.crt" ]; then
    echo "🔐 Gerando certificado autoassinado para desenvolvimento..."
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout ssl/nginx-selfsigned.key \
        -out ssl/nginx-selfsigned.crt \
        -subj "/C=PT/ST=Lisboa/L=Lisboa/O=ACR Gestao/CN=localhost"

    echo "✅ Certificado autoassinado criado"
fi

# Gerar dhparam se não existir
if [ ! -f "ssl/dhparam.pem" ]; then
    echo "🔐 Gerando dhparam (pode demorar alguns minutos)..."
    openssl dhparam -out ssl/dhparam.pem 2048
    echo "✅ dhparam criado"
fi

# Função para obter certificados Let's Encrypt
setup_letsencrypt() {
    echo "🌐 Configurando certificados Let's Encrypt..."

    # Primeiro, obter certificados
    for domain in $DOMAINS; do
        echo "📜 Obtendo certificado para $domain..."
        docker-compose -f docker-compose.yml -f docker-compose.nginx.yml --profile ssl \
            run --rm certbot certonly \
            --webroot --webroot-path=/var/www/certbot \
            --email "$EMAIL" --agree-tos --no-eff-email \
            -d "$domain" || echo "⚠️ Falha ao obter certificado para $domain"
    done

    # Atualizar nginx.conf para usar certificados Let's Encrypt
    sed -i.bak \
        -e 's|ssl_certificate /etc/ssl/certs/nginx-selfsigned.crt;|ssl_certificate /etc/letsencrypt/live/acrsantatecla.duckdns.org/fullchain.pem;|' \
        -e 's|ssl_certificate_key /etc/ssl/private/nginx-selfsigned.key;|ssl_certificate_key /etc/letsencrypt/live/acrsantatecla.duckdns.org/privkey.pem;|' \
        -e 's|ssl_dhparam /etc/ssl/certs/dhparam.pem;|ssl_dhparam /etc/ssl/dhparam.pem;|' \
        nginx.conf

    echo "✅ Certificados Let's Encrypt configurados"
}

# Verificar se é produção ou desenvolvimento
if [ "$1" = "production" ]; then
    setup_letsencrypt
else
    echo "ℹ️ Modo desenvolvimento - usando certificados autoassinados"
    echo "ℹ️ Para produção, execute: ./setup_ssl.sh production"
fi

echo "✅ Configuração SSL concluída!"
echo ""
echo "📋 Próximos passos:"
echo "   1. ./deploy_nginx.sh (para deploy com Nginx)"
echo "   2. Configurar DNS dos domínios para o IP do servidor"
echo "   3. ./setup_ssl.sh production (para certificados válidos)"
