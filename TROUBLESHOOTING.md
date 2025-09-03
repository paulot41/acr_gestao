# Guia de Resolução - Problema "empty compose file"

## O que aconteceu
O arquivo `docker-compose.base-nginx.yml` ficou vazio no servidor de produção, causando o erro "empty compose file" ao tentar usar docker-compose.

## Causa provável
- Edição acidental (abrir e salvar vazio)
- Uso acidental de redirecionamento (`> docker-compose.base-nginx.yml`)
- Transferência de arquivo interrompida (scp/rsync)
- Conflito de merge mal resolvido

## Solução imediata
```bash
# Restaurar do repositório Git
git fetch origin main
git reset --hard origin/main

# Verificar se foi restaurado
cat docker-compose.base-nginx.yml | head -5
```

## Verificações implementadas

### 1. Validação automática no deploy
O script `deploy_nginx.sh` agora valida o arquivo antes de qualquer operação:
- Verifica se o arquivo não está vazio
- Confirma se contém a seção `services:`
- Cria backup automático antes do deploy

### 2. Script de validação independente
```bash
./validate_compose.sh
```
Valida todos os arquivos docker-compose e verifica:
- Existência do arquivo
- Conteúdo não vazio
- Sintaxe YAML válida
- Presença dos serviços essenciais (web, db, nginx)

### 3. Script de recuperação automática
```bash
./recover.sh
```
Tenta recuperar o arquivo automaticamente:
1. Primeiro do repositório Git
2. Depois do backup mais recente
3. Informa se recuperação manual é necessária

## Prevenção futura

### Para administradores:
1. **Sempre use Git**: Edite arquivos localmente e faça push, depois pull no servidor
2. **Nunca edite diretamente**: Evite editar `docker-compose.base-nginx.yml` diretamente no servidor
3. **Execute validação**: Use `./validate_compose.sh` antes de deploy crítico
4. **Backups automáticos**: O deploy agora cria backups em `backups/`

### Scripts disponíveis:
- `./deploy_nginx.sh` - Deploy com validação automática
- `./validate_compose.sh` - Validar arquivos docker-compose
- `./recover.sh` - Recuperação automática
- `./test_system.sh` - Teste do sistema (agora com validação)

## Monitoramento
Os logs do nginx mostram códigos HTTP:
- `400` = Problemas de configuração Django (ALLOWED_HOSTS)
- `301` = Redirect HTTP→HTTPS (normal)
- `404` = Rota não existe (normal para `/` em Django)

## Em caso de problemas
1. Execute `./recover.sh` primeiro
2. Se falhar, verifique conectividade Git
3. Como último recurso, restaure de backup conhecido
4. Contacte equipe de desenvolvimento se necessário
