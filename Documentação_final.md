[Documentacao_Final.md](https://github.com/user-attachments/files/27102620/Documentacao_Final.md)
# DOCUMENTAÇÃO FINAL — Detalhes Operacionais
**Inovatus Sistemas — voosuporte.com.br — Abril/2026**

---

## ÍNDICE
1. Arquivos de Configuração do Projeto
2. Acesso SSH ao Servidor
3. APIs Internas (portal-stats e notificações)
4. Lógica de Numeração Sequencial das O.S
5. DNS e Domínio (Hostinger)
6. Supabase Storage (bucket evidencias)
7. Como Adicionar Novo Ano na Sequência
8. Estratégia de Backup (URGENTE)
9. Variáveis de Ambiente para Desenvolvimento Local
10. Resumo de Tudo — Checklist Final

---

## 1. ARQUIVOS DE CONFIGURAÇÃO DO PROJETO

### requirements.txt (dependências Python)

```txt
fastapi
uvicorn[standard]
python-dotenv
supabase
python-multipart
jinja2
weasyprint
resend
python-dateutil
```

Para instalar:
```bash
pip install -r requirements.txt
```

Para gerar o arquivo com versões exatas (recomendado após qualquer install):
```bash
pip freeze > requirements.txt
```

### atualizar.sh (script de deploy)

```bash
#!/bin/bash
cd /root/suporte-chamados
git pull
systemctl restart suporte
echo "✅ Sistema atualizado em $(date)"
```

Permissão de execução:
```bash
chmod +x /root/suporte-chamados/atualizar.sh
```

### .gitignore

```gitignore
# Ambiente virtual
venv/

# Variáveis de ambiente (NUNCA versionar)
.env

# Uploads de usuários (arquivos grandes)
static/uploads/

# Cache Python
__pycache__/
*.pyc
*.pyo

# Arquivos de sistema
.DS_Store
Thumbs.db

# Logs
*.log

# IDEs
.vscode/
.idea/
```

### .env.example (modelo para novos desenvolvedores)

Criar este arquivo no repositório (sem valores reais) para guiar novos devs:

```env
# Supabase
SUPABASE_URL=https://SEU_PROJECT_ID.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...  # Chave anon
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...  # Chave service_role

# Resend (envio de e-mail)
RESEND_KEY=re_XXXXXXXXXXXXXXXXXXXXXXXX
```

---

## 2. ACESSO SSH AO SERVIDOR

### Conectar ao servidor

```bash
ssh root@187.127.28.178
```

Se configurado com chave SSH:
```bash
ssh -i ~/.ssh/sua_chave_privada root@187.127.28.178
```

### Configurar acesso rápido (opcional)

Adicionar no `~/.ssh/config` do computador local:

```
Host inovatus
    HostName 187.127.28.178
    User root
    IdentityFile ~/.ssh/sua_chave_privada
```

Depois: `ssh inovatus`

### Primeiro acesso de um novo programador

```bash
# No servidor, adicionar a chave pública do novo dev
nano ~/.ssh/authorized_keys
# Colar a chave pública do novo dev (conteúdo de id_rsa.pub ou similar)
```

### Transferir arquivos para o servidor (se necessário)

```bash
# Enviar arquivo local para o servidor
scp arquivo.py root@187.127.28.178:/root/suporte-chamados/

# Baixar arquivo do servidor
scp root@187.127.28.178:/root/suporte-chamados/main.py ./main.py
```

---

## 3. APIs INTERNAS

### GET /api/meu-email

Retorna os dados do usuário logado. Usado em todos os templates para saber quem está logado.

```python
# Resposta
{
    "email": "fulano@email.com",
    "nome": "Fulano de Tal",
    "role": "admin",                           # ou "colaborador"
    "modulos": ["chamados", "ordens_servico"], # array de módulos
    "cargo": "Técnico de Suporte",
    "departamento_id": "uuid-aqui"
}
```

### GET /api/portal-stats

Retorna contadores para os cards do portal. Chamada logo após `/api/meu-email`.

```python
# Resposta
{
    # Chamados
    "chamados_abertos": 5,          # aberto + em_analise + reaberto
    "chamados_aguardando": 2,       # aguardando_colaborador
    "chamados_sla_vencido": 1,      # abertos com SLA vencido

    # O.S (colaborador)
    "os_pendentes": 3,              # emitidas aguardando aprovação
    "os_prestacao": 1,              # prestações devolvidas

    # Financeiro
    "financeiro_pendentes": 4,      # O.S aguardando aprovação financeiro
    "prestacoes_analisar": 2,       # prestações para analisar
    "contas_vencendo": 1,           # contas vencendo em 7 dias
}
```

### GET /api/notificacoes

Verifica se há notificações pendentes para o usuário logado. Chamada a cada 30 segundos pelo frontend.

```python
# Resposta
{
    "total": 3,
    "itens": [
        {"tipo": "chamado_aguardando", "texto": "Chamado #AB12CD34 aguarda sua resposta"},
        {"tipo": "prestacao_devolvida", "texto": "Prestação devolvida na O.S 005/2026"},
    ]
}
```

Como o frontend usa:
```javascript
// Em meus_chamados.html e colaborador_os.html
setInterval(async () => {
    const data = await fetch('/api/notificacoes').then(r => r.json());
    const badge = document.getElementById('notif-badge');
    if (data.total > 0) {
        badge.textContent = data.total;
        badge.classList.add('show');
        // Dispara notificação push do navegador
        if (Notification.permission === 'granted' && data.total > ultimoTotal) {
            new Notification('🔔 Suporte Técnico', {
                body: data.itens[0]?.texto || 'Você tem notificações pendentes!'
            });
        }
    } else {
        badge.classList.remove('show');
    }
    ultimoTotal = data.total;
}, 30000); // 30 segundos
```

---

## 4. LÓGICA DE NUMERAÇÃO SEQUENCIAL DAS O.S

### Como funciona

A tabela `os_sequencia` mantém o último número usado por ano:

```sql
-- Exemplo do estado atual
SELECT * FROM os_sequencia;
-- id | ano  | ultimo_numero
-- ... | 2026 | 12
```

### Endpoint de incremento (GET /api/os/proximo-numero)

```python
@app.get("/api/os/proximo-numero")
async def proximo_numero(request: Request):
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=401)

    ano = datetime.now().year

    # Busca registro do ano atual
    seq = supabase.table("os_sequencia").select("*").eq("ano", ano).execute()

    if not seq.data:
        # Primeiro uso do ano — criar registro
        supabase.table("os_sequencia").insert({"ano": ano, "ultimo_numero": 1}).execute()
        ultimo = 1
    else:
        # Incrementar
        ultimo = seq.data[0]["ultimo_numero"] + 1
        supabase.table("os_sequencia").update(
            {"ultimo_numero": ultimo}
        ).eq("ano", ano).execute()

    # Formatar: 001/2026
    numero = f"{str(ultimo).zfill(3)}/{ano}"
    return {"numero": numero, "sequencial": ultimo}
```

### Endpoint de preview (GET /api/os/proximo-numero-preview)

Igual ao acima mas **sem incrementar**. Usado para exibir o próximo número antes de criar a O.S.

```python
# Apenas lê, não atualiza
seq = supabase.table("os_sequencia").select("*").eq("ano", ano).execute()
ultimo = (seq.data[0]["ultimo_numero"] + 1) if seq.data else 1
numero = f"{str(ultimo).zfill(3)}/{ano}"
return {"numero": numero}
```

### Como o formulário usa

```javascript
// os_nova.html — ao carregar a página
async function carregarProximoNumero() {
    const res = await fetch('/api/os/proximo-numero-preview');
    const data = await res.json();
    document.getElementById('numero-preview').textContent = data.numero;
}

// Ao confirmar emissão — o backend chama /proximo-numero (incrementa)
// e salva o número na O.S
```

---

## 5. DNS E DOMÍNIO (Hostinger)

### Registros DNS configurados

Acessar em: **Hostinger → Domínios → voosuporte.com.br → DNS Zone**

| Tipo | Nome | Valor | Uso |
|------|------|-------|-----|
| A | @ | 187.127.28.178 | Site principal |
| A | www | 187.127.28.178 | www.voosuporte.com.br |
| MX | @ | (Resend fornece) | Recebimento de e-mail |
| TXT | @ | v=spf1 include:resend.com ~all | SPF — autenticação de envio |
| TXT | resend._domainkey | (Resend fornece) | DKIM — assinatura de e-mail |
| TXT | _dmarc | v=DMARC1; p=none; rua=mailto:... | DMARC — política de e-mail |

### Verificar registros DNS (terminal)

```bash
# Verificar A record
dig voosuporte.com.br A

# Verificar SPF
dig voosuporte.com.br TXT

# Verificar DKIM do Resend
dig resend._domainkey.voosuporte.com.br TXT

# Verificar MX
dig voosuporte.com.br MX
```

### Se o e-mail parar de funcionar

1. Acessar dashboard do Resend (resend.com)
2. Ir em "Domains" → voosuporte.com.br
3. Verificar se todos os registros estão "Verified" (verde)
4. Se algum estiver vermelho, reconfigurar o registro DNS na Hostinger
5. Aguardar propagação (até 24h)

---

## 6. SUPABASE STORAGE (bucket evidencias)

### Configuração atual

| Item | Valor |
|------|-------|
| Nome do bucket | evidencias |
| Acesso | Público (public bucket) |
| Limite por arquivo | 524.288.000 bytes (500MB) — via SQL |
| Status | Configurado mas pouco usado (uploads vão para servidor local) |

### Por que o bucket está pouco usado

O plano gratuito do Supabase tem limite de **50MB por arquivo** na interface, mas via SQL conseguimos aumentar para 500MB no metadado. Na prática, optamos por salvar tudo no servidor local para evitar problemas. O bucket ainda existe caso seja necessário no futuro.

### Como verificar o bucket

No painel do Supabase: **Storage → Buckets → evidencias**

```sql
-- Ver configuração atual do bucket
SELECT id, name, public, file_size_limit, allowed_mime_types
FROM storage.buckets
WHERE id = 'evidencias';
```

### Se precisar usar o Supabase Storage novamente

```python
# Upload para o Supabase (código antigo — não está em uso)
supabase.storage.from_("evidencias").upload(nome, conteudo)
url = supabase.storage.from_("evidencias").get_public_url(nome)
```

---

## 7. COMO ADICIONAR NOVO ANO NA SEQUÊNCIA

No início de cada ano, a tabela `os_sequencia` precisa ter um registro para o novo ano.
O sistema cria automaticamente se não existir, mas é boa prática criar manualmente.

### Criar registro para novo ano (ex: 2027)

No **SQL Editor do Supabase:**

```sql
-- Adicionar novo ano
INSERT INTO os_sequencia (ano, ultimo_numero)
VALUES (2027, 0);

-- Verificar
SELECT * FROM os_sequencia ORDER BY ano;

-- Se quiser redefinir o número de um ano existente
UPDATE os_sequencia SET ultimo_numero = 0 WHERE ano = 2027;

-- Forçar começar do número específico (ex: continuar de 50)
UPDATE os_sequencia SET ultimo_numero = 50 WHERE ano = 2027;
-- A próxima O.S será 051/2027
```

### Alterar numeração via interface

Em `/configuracoes` → aba "Numeração O.S" → campo "Próximo número" → Salvar.

---

## 8. ESTRATÉGIA DE BACKUP (⚠️ URGENTE — NÃO CONFIGURADO)

**Atualmente o sistema NÃO tem backup automático configurado.**
Se o servidor falhar ou os dados forem deletados acidentalmente, não há recuperação.

### Dados em risco

| Dado | Localização | Risco |
|------|------------|-------|
| Banco de dados | Supabase (nuvem) | Médio — Supabase faz backup interno |
| Arquivos enviados | /root/suporte-chamados/static/uploads/ | **ALTO — sem backup nenhum** |
| Código fonte | GitHub | Baixo — versionado |
| Configurações | /etc/nginx/, /etc/systemd/ | Médio |

### Solução recomendada — Backup diário simples

Adicionar este script no servidor:

```bash
# Criar script de backup
cat > /root/backup.sh << 'EOF'
#!/bin/bash
DATA=$(date +%Y-%m-%d)
DESTINO="/root/backups/$DATA"
mkdir -p $DESTINO

# Backup dos uploads
tar -czf $DESTINO/uploads.tar.gz /root/suporte-chamados/static/uploads/

# Backup das configurações
cp /etc/nginx/sites-enabled/voosuporte.com.br $DESTINO/nginx.conf
cp /etc/systemd/system/suporte.service $DESTINO/suporte.service
cp /root/suporte-chamados/.env $DESTINO/env.bak

# Remover backups mais antigos que 7 dias
find /root/backups -maxdepth 1 -type d -mtime +7 -exec rm -rf {} \;

echo "✅ Backup concluído: $DESTINO"
EOF

chmod +x /root/backup.sh
mkdir -p /root/backups

# Agendar backup diário às 3h da manhã
crontab -e
# Adicionar linha:
# 0 3 * * * /root/backup.sh >> /var/log/backup.log 2>&1
```

### Backup do banco de dados Supabase

O Supabase Pro faz backup automático com retenção de 7 dias.
No plano gratuito, fazer backup manual periodicamente:

```bash
# Instalar pg_dump se necessário
apt-get install postgresql-client

# Fazer dump (substituir credenciais)
pg_dump "postgresql://postgres:[SENHA]@db.wvjsbgfnhdapqtinewgb.supabase.co:5432/postgres" \
    > /root/backups/banco_$(date +%Y-%m-%d).sql
```

A string de conexão está em: **Supabase → Settings → Database → Connection string**

### Backup remoto (recomendado)

Enviar os backups para um serviço externo como Backblaze B2, AWS S3 ou Google Drive garante que um problema no servidor não perca os backups também.

---

## 9. VARIÁVEIS DE AMBIENTE PARA DESENVOLVIMENTO LOCAL

Criar um arquivo `.env` local com valores de **desenvolvimento** (não usar o banco de produção):

```env
# Opção 1: Usar banco de produção (cuidado — dados reais)
SUPABASE_URL=https://wvjsbgfnhdapqtinewgb.supabase.co
SUPABASE_KEY=eyJ...     # Pegar no painel do Supabase
SUPABASE_SERVICE_KEY=eyJ...
RESEND_KEY=re_...       # Pegar no painel do Resend

# Opção 2: Criar projeto Supabase separado para dev (recomendado)
SUPABASE_URL=https://SEU_PROJETO_DEV.supabase.co
SUPABASE_KEY=eyJ...
SUPABASE_SERVICE_KEY=eyJ...
RESEND_KEY=re_...       # Mesma chave — e-mails em dev não causam problemas
```

### Ajuste necessário para desenvolvimento local

No `main.py`, a função `fazer_upload()` gera URLs absolutas de produção. Em dev, ajustar:

```python
async def fazer_upload(arquivo: UploadFile) -> str:
    if not arquivo or not arquivo.filename:
        return ""
    conteudo = await arquivo.read()
    nome = f"{os.urandom(8).hex()}_{arquivo.filename}"
    pasta = "static/uploads"  # Relativo em dev
    os.makedirs(pasta, exist_ok=True)
    with open(f"{pasta}/{nome}", "wb") as f:
        f.write(conteudo)

    # Em produção usa URL absoluta
    BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
    return f"{BASE_URL}/static/uploads/{nome}"
```

Adicionar no `.env`:
```env
BASE_URL=http://localhost:8000   # dev
# BASE_URL=https://voosuporte.com.br  # produção
```

### Rodar localmente com reload automático

```bash
# Ativa o ambiente virtual
source venv/bin/activate

# Roda com reload (reinicia ao salvar qualquer arquivo)
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Acessar em: http://localhost:8000
```

---

## 10. CHECKLIST FINAL — TUDO QUE O PROGRAMADOR PRECISA

### Acessos necessários (solicitar ao Jocirio)

- [ ] Convite para o repositório GitHub: github.com/Jocirio/suporte-chamados
- [ ] Credenciais do `.env` (SUPABASE_KEY, SUPABASE_SERVICE_KEY, RESEND_KEY)
- [ ] Senha ou chave SSH do servidor: root@187.127.28.178
- [ ] Acesso ao painel Supabase: supabase.com (projeto wvjsbgfnhdapqtinewgb)
- [ ] Acesso ao painel Resend: resend.com
- [ ] Acesso ao painel Hostinger: DNS e VPS

### Primeiros passos no projeto

```bash
# 1. Clonar repositório
git clone https://github.com/Jocirio/suporte-chamados.git
cd suporte-chamados

# 2. Criar ambiente virtual
python3 -m venv venv
source venv/bin/activate

# 3. Instalar dependências
pip install -r requirements.txt

# 4. Criar .env com as credenciais recebidas
cp .env.example .env
nano .env   # Preencher com os valores reais

# 5. Criar pasta de uploads
mkdir -p static/uploads

# 6. Rodar
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 7. Acessar http://localhost:8000 e fazer login
```

### Documentação disponível

| Arquivo | Conteúdo |
|---------|---------|
| `Documentacao_Tecnica_Completa_Inovatus.md` | Infraestrutura, banco, módulos, rotas, fluxos, e-mail, manutenção, comandos, SQL |
| `Guia_Templates_HTML_Inovatus.md` | Todos os 22 templates com estrutura, JavaScript e CSS |
| `Documentacao_Complementar_Inovatus.md` | Estrutura do main.py, schema detalhado, WeasyPrint, templates de e-mail, padrões de erro, referência CSS, cron, SSL |
| `Documentacao_Final_Inovatus.md` (este arquivo) | Arquivos de config, SSH, APIs internas, numeração O.S, DNS, backup, dev local |

### Resumo do sistema em 5 linhas

> Sistema web Python/FastAPI + Supabase para gestão de chamados técnicos de saúde pública.
> Tem 4 módulos: Chamados (suporte), O.S (viagens), Financeiro (aprovações/contas) e Colaborador (app mobile).
> Todos os arquivos enviados vão para `/static/uploads/` no servidor e são servidos pelo Nginx.
> A autenticação é via JWT do Supabase armazenado em cookie httpOnly.
> O único arquivo de código é o `main.py` — contém todas as rotas, lógica e envio de e-mails.

---

*Documentação Final — Abril/2026 — Inovatus Sistemas*
*Contato: jocirioarruda@gmail.com | voosuporte.com.br*
