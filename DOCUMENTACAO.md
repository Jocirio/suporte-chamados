[Documentacao_Tecnica_Completa_voosuporte.md](https://github.com/user-attachments/files/27102286/Documentacao_Tecnica_Completa_voosuporte.md)
# DOCUMENTAÇÃO TÉCNICA COMPLETA — Inovatus Sistemas
**Sistema de Suporte Técnico + Ordens de Serviço + Financeiro**
**voosuporte.com.br — Abril/2026**

---

## ÍNDICE
1. Visão Geral
2. Infraestrutura do Servidor
3. Configuração do Nginx (arquivo completo)
4. Configuração do Systemd
5. Variáveis de Ambiente
6. Banco de Dados (Supabase)
7. Autenticação — Fluxo Completo
8. Upload de Arquivos — Função Atual
9. Módulos do Sistema
10. Estrutura de Arquivos do Projeto
11. Templates HTML — Lista Completa
12. Rotas da API (main.py)
13. Fluxos de Status
14. Como o Frontend Chama a API
15. E-mail (Resend)
16. Como Rodar Localmente
17. Manutenção e Comandos
18. SQL Importantes Aplicados no Supabase
19. Problemas Comuns e Soluções
20. Pendências e Melhorias Futuras

---

## 1. Visão Geral

Sistema web desenvolvido em **Python/FastAPI** para gerenciamento de chamados técnicos de suporte a sistemas de saúde pública (ESF/PACS), com módulo completo de **Ordens de Serviço** e módulo **Financeiro**.

| Item | Valor |
|------|-------|
| URL de Produção | https://voosuporte.com.br |
| IP VPS | 187.127.28.178 |
| Repositório GitHub | https://github.com/Jocirio/suporte-chamados |
| Supabase Project ID | wvjsbgfnhdapqtinewgb |
| Supabase URL | https://wvjsbgfnhdapqtinewgb.supabase.co |
| Usuário Admin | jocirioarruda@gmail.com |
| Serviço systemd | suporte.service |
| Diretório do projeto | /root/suporte-chamados |
| Script de atualização | /root/suporte-chamados/atualizar.sh |

### Stack Tecnológica

| Componente | Tecnologia |
|-----------|-----------|
| Backend | Python 3.12 + FastAPI + Uvicorn |
| Banco de Dados | Supabase (PostgreSQL) |
| Storage de arquivos | Servidor local /root/suporte-chamados/static/uploads/ |
| Autenticação | Supabase Auth (JWT via cookie httpOnly) |
| E-mail | Resend (domínio voosuporte.com.br verificado com DKIM/SPF/DMARC) |
| Geração de PDF | WeasyPrint |
| Frontend | HTML + CSS + JavaScript puro (sem frameworks) |
| Proxy reverso | Nginx |
| SSL | Let's Encrypt (válido até 24/07/2026) |
| Ambiente Python | virtualenv em /root/suporte-chamados/venv/ |

---

## 2. Infraestrutura do Servidor

**VPS:** Hostinger — Ubuntu 24.04 LTS

### Estrutura de diretórios no servidor

```
/root/suporte-chamados/
├── main.py                  # Arquivo principal — todas as rotas
├── .env                     # Variáveis de ambiente (não versionado)
├── requirements.txt         # Dependências Python
├── atualizar.sh             # Script de atualização (git pull + restart)
├── venv/                    # Ambiente virtual Python
├── templates/               # Templates HTML (Jinja2)
│   ├── login.html
│   ├── registrar.html
│   ├── portal.html
│   ├── configuracoes_gerais.html
│   ├── formulario.html
│   ├── dashboard.html
│   ├── meus_chamados.html
│   ├── clientes.html
│   ├── usuarios.html
│   ├── relatorios.html
│   ├── os_dashboard.html
│   ├── os_nova.html
│   ├── os_config.html
│   ├── os_financeiro.html
│   ├── financeiro_dashboard.html
│   ├── financeiro_ordens.html
│   ├── financeiro_nova_os.html
│   ├── financeiro_prestacoes.html
│   ├── financeiro_adiantamentos.html
│   ├── financeiro_contas.html
│   ├── financeiro_relatorios.html
│   └── colaborador_os.html
└── static/
    └── uploads/             # Arquivos enviados (imagens, vídeos, PDFs)
```

---

## 3. Configuração do Nginx (arquivo completo)

**Arquivo:** `/etc/nginx/sites-enabled/voosuporte.com.br`

```nginx
server {
    listen 80;
    server_name voosuporte.com.br www.voosuporte.com.br;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name voosuporte.com.br www.voosuporte.com.br;

    ssl_certificate /etc/letsencrypt/live/voosuporte.com.br/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/voosuporte.com.br/privkey.pem;

    client_max_body_size 500M;
    include /etc/nginx/mime.types;
    default_type application/octet-stream;
    proxy_read_timeout 300;
    proxy_connect_timeout 300;
    proxy_send_timeout 300;

    location /static/uploads/ {
        alias /root/suporte-chamados/static/uploads/;
        add_header Content-Disposition inline;
        types {
            application/pdf pdf;
            video/mp4 mp4;
            video/quicktime mov;
            image/jpeg jpg jpeg;
            image/png png;
            image/gif gif;
        }
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Comandos Nginx
```bash
nginx -t                        # Validar configuração
systemctl reload nginx          # Recarregar sem derrubar
systemctl restart nginx         # Reiniciar completamente
```

---

## 4. Configuração do Systemd

**Arquivo:** `/etc/systemd/system/suporte.service`

```ini
[Unit]
Description=Suporte Chamados
After=network.target

[Service]
User=root
WorkingDirectory=/root/suporte-chamados
ExecStart=/root/suporte-chamados/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --timeout-keep-alive 300
Restart=always

[Install]
WantedBy=multi-user.target
```

### Comandos do serviço
```bash
systemctl start suporte
systemctl stop suporte
systemctl restart suporte
systemctl status suporte
systemctl enable suporte      # Habilitar inicialização automática
journalctl -u suporte -f      # Ver logs ao vivo
journalctl -u suporte -n 50 --no-pager
```

### Script de atualização (atualizar.sh)
```bash
#!/bin/bash
cd /root/suporte-chamados
git pull
systemctl restart suporte
```

---

## 5. Variáveis de Ambiente (.env)

Arquivo localizado em `/root/suporte-chamados/.env`. **Nunca versionar este arquivo.**

```env
SUPABASE_URL=https://wvjsbgfnhdapqtinewgb.supabase.co
SUPABASE_KEY=eyJ...           # Chave anon pública
SUPABASE_SERVICE_KEY=eyJ...   # Chave service_role (acesso admin, nunca expor)
RESEND_KEY=re_...             # API Key do Resend
```

### Como carregar no main.py
```python
from dotenv import load_dotenv
import os
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
RESEND_KEY = os.getenv("RESEND_KEY")
```

---

## 6. Banco de Dados (Supabase)

> **IMPORTANTE:** RLS (Row Level Security) está **DESABILITADO** nas tabelas financeiras. Acesso controlado pelo backend.

### 6.1 Módulo Chamados

| Tabela | Principais colunas |
|--------|-------------------|
| chamados_controle | id, colaborador_email, cliente_nome, unidade, descricao_tecnica, status, prioridade, categoria, qualitor_id, sla_horas, evidencia_url, created_at, ultima_interacao |
| chamados_historico | id, chamado_id, evento, descricao, autor, created_at |
| chamados_mensagens | id, chamado_id, tipo (abertura/pedido_info/resposta/complemento), mensagem, evidencia_url, created_at |
| chamados_participantes | id, chamado_id, email, added_at |
| perfis | id, email, nome, role (admin/colaborador), modulos (JSONB array), cargo, departamento_id, ativo |
| clientes | id, nome (município), uf, distancia_km |

### 6.2 Módulo Ordens de Serviço

| Tabela | Principais colunas |
|--------|-------------------|
| os_departamentos | id, nome, valor_diaria, valor_meia_diaria |
| os_ordens | id, numero, colaborador_email, colaborador_nome, departamento_id, municipio_id, municipio_nome, data_saida, data_retorno, dias, diarias, meia_diaria, valor_total, status, adiantamentos (JSONB), created_at |
| os_prestacao_contas | id, os_id, colaborador_email, tipo, descricao, valor, status (pendente/aprovado/devolvido), comprovante_urls (JSONB array), aprovado_por, aprovado_em |
| os_custos_empresa | id, os_id, tipo, descricao, valor, created_at |
| os_sequencia | id, ano, ultimo_numero |
| os_tipos_transporte | id, nome |
| os_tipos_adiantamento | id, nome |

### 6.3 Módulo Financeiro (RLS DESABILITADO)

| Tabela | Principais colunas |
|--------|-------------------|
| os_adiantamentos_avulsos | id, colaborador_email, valor, descricao, data, created_at |
| financeiro_contas | id, tipo (pagar/receber), descricao, valor, vencimento, status (pendente/pago), pago_em |

### 6.4 Campo `modulos` na tabela `perfis`

Array JSONB. Exemplos:
```json
["chamados"]
["chamados", "ordens_servico"]
["financeiro"]
["colaborador"]
["chamados", "ordens_servico", "financeiro"]
```

| Valor | Acesso |
|-------|--------|
| chamados | Módulo de chamados — /meus-chamados e /novo-chamado |
| ordens_servico | Módulo O.S — /os e subpáginas |
| financeiro | Módulo financeiro — /financeiro e subpáginas |
| colaborador | Minhas Viagens — /colaborador/os |

---

## 7. Autenticação — Fluxo Completo

```
1. Usuário faz POST /login com email + senha
2. Backend chama: supabase.auth.sign_in_with_password({"email": email, "password": senha})
3. Supabase retorna: session.access_token (JWT)
4. Backend seta cookies httpOnly:
   - "token" = access_token (JWT do Supabase)
   - "role" = "admin" ou "colaborador" (lido do perfil)
5. Em cada rota protegida:
   token = request.cookies.get("token")
   if not token: return RedirectResponse(url="/")
   user = supabase.auth.get_user(token)  # Valida o JWT
6. Token expira após algumas horas — usuário precisa fazer logout/login
```

### Verificação de módulo nas rotas
```python
@app.get("/financeiro")
async def financeiro(request: Request):
    token = request.cookies.get("token")
    if not token:
        return RedirectResponse(url="/")
    user = supabase.auth.get_user(token)
    perfil = supabase.table("perfis").select("modulos").eq("email", user.user.email).execute()
    modulos = perfil.data[0].get("modulos", []) if perfil.data else []
    if "financeiro" not in modulos:
        return RedirectResponse(url="/portal")
    return templates.TemplateResponse(request=request, name="financeiro_dashboard.html")
```

---

## 8. Upload de Arquivos — Função Atual (fazer_upload)

Esta função está no `main.py` e é chamada sempre que há upload. **Versão atual salva tudo localmente:**

```python
async def fazer_upload(arquivo: UploadFile) -> str:
    """
    Salva arquivo no servidor local e retorna URL pública.
    Todos os tipos de arquivo vão para /static/uploads/
    Limite: 500MB (configurado no Nginx)
    """
    if not arquivo or not arquivo.filename:
        return ""
    conteudo = await arquivo.read()
    nome = f"{os.urandom(8).hex()}_{arquivo.filename}"
    pasta = "/root/suporte-chamados/static/uploads"
    os.makedirs(pasta, exist_ok=True)
    with open(f"{pasta}/{nome}", "wb") as f:
        f.write(conteudo)
    return f"https://voosuporte.com.br/static/uploads/{nome}"
```

> **NOTA:** Anteriormente a função enviava para o Supabase Storage (bucket `evidencias`). Foi alterada para servidor local porque o plano gratuito do Supabase tem limite de 50MB por arquivo. PDFs antigos ainda estão no Supabase e podem apresentar erro ao abrir.

### Permissões necessárias na pasta
```bash
chmod 755 /root
chmod 755 /root/suporte-chamados/static/uploads/
chmod 644 /root/suporte-chamados/static/uploads/*
```

---

## 9. Módulos do Sistema

### 9.1 Chamados
Gerenciamento de chamados técnicos para sistemas de saúde (ESF, PACS, etc.).

- Abertura com múltiplos anexos (imagens, vídeos, PDFs) via XHR com barra de progresso
- Fluxo: `aberto → em_analise → aguardando_colaborador → pendente_dev → fechado`
- Vinculação com ID Qualitor (sistema externo de tickets)
- SLA configurável por chamado (padrão 48h)
- Participantes adicionais por chamado
- Conversa em thread com histórico completo
- Notificações por e-mail automáticas
- Busca global em mensagens
- Impressão da conversa (window.print)
- Relatório semanal automático via cron

### 9.2 Ordens de Serviço
Gerenciamento de viagens e deslocamentos para técnicos de campo.

- Numeração sequencial por ano: `NNN/AAAA` (ex: 001/2026)
- Cálculo automático: `dias × diária + meias × meia_diária + adiantamentos`
- Múltiplos adiantamentos por O.S (armazenados como JSONB)
- Fluxo: `emitida → aprovada → prestacao_enviada → prestacao_aprovada → encerrada`
  - Desvios: `prestacao_devolvida`, `cancelada`
- PDF da O.S gerado com WeasyPrint (rota: `/os/ordens/{id}/pdf`)
- E-mails automáticos ao colaborador em cada etapa do fluxo

### 9.3 Financeiro
Painel financeiro completo para gestão das O.S e contas.

- Dashboard com alertas de pendências (O.S aguardando aprovação, contas vencendo, etc.)
- Aprovação, cancelamento e reabertura de O.S
- Emissão de O.S pelo financeiro (já aprovada automaticamente, sem etapa `emitida`)
- Análise item a item de prestações de contas (aprovar ou devolver com justificativa)
- Custos pagos pela empresa por O.S (hotel, passagem, etc.) — tabela `os_custos_empresa`
- Adiantamentos avulsos (fora de O.S) por colaborador
- Contas a pagar e receber com alertas de vencimento
- Relatórios em PDF com 5 tipos: geral, por colaborador, por cliente, contas, adiantamentos

### 9.4 Colaborador — Minhas Viagens (`/colaborador/os`)
Interface mobile-first para colaboradores em campo.

- Dashboard: O.S no ano, dias viajados, valor de diárias, km percorridos
- Ranking top 5 municípios visitados
- Visualização das próprias O.S (filtradas por e-mail via `?meu=1` na API)
- Envio de prestação de contas com múltiplos anexos
- Câmera mobile integrada para captura de comprovantes
- Bottom navigation com 4 abas: Dashboard, Viagens, Prestações, Perfil
- Totalmente responsivo para celular

---

## 10. Estrutura de Arquivos do Projeto

```
suporte-chamados/
├── main.py                   # ARQUIVO PRINCIPAL — todas as rotas FastAPI
├── .env                      # Credenciais (não versionado)
├── .gitignore                # Exclui .env, venv/, __pycache__/, static/uploads/
├── requirements.txt          # pip install -r requirements.txt
├── atualizar.sh              # Deploy rápido
├── venv/                     # Ambiente Python (não versionado)
├── templates/                # HTML renderizados pelo Jinja2
└── static/
    └── uploads/              # Arquivos enviados pelos usuários (não versionado)
```

### Dependências principais (requirements.txt)
```
fastapi
uvicorn
python-dotenv
supabase
python-multipart
jinja2
weasyprint
resend
```

---

## 11. Templates HTML — Lista Completa e Função

| Arquivo | Rota | Módulo | Função |
|---------|------|--------|--------|
| login.html | / | Público | Tela de login |
| registrar.html | /registrar | Público | Cadastro de usuário |
| portal.html | /portal | Autenticado | Hub central — exibe cards dos módulos conforme perfil |
| configuracoes_gerais.html | /configuracoes | Admin | Configurar equipe, municípios, departamentos, numeração O.S |
| formulario.html | /novo-chamado | Autenticado | Abertura de chamado com múltiplos anexos + barra de progresso XHR |
| dashboard.html | /admin | Admin | Dashboard com todos os chamados + filtros + modal de conversa |
| meus_chamados.html | /meus-chamados | Autenticado | Visão do colaborador dos seus chamados |
| clientes.html | /admin/clientes | Admin | Gestão de clientes/municípios |
| usuarios.html | /admin/usuarios | Admin | Gestão de usuários e perfis |
| relatorios.html | /relatorios | Admin | Relatórios de chamados |
| os_dashboard.html | /os | ordens_servico | Dashboard de O.S com lista e filtros |
| os_nova.html | /os/nova | ordens_servico | Emissão de nova O.S |
| os_config.html | /os/config | ordens_servico | Configurações do módulo O.S |
| os_financeiro.html | /os/financeiro | ordens_servico | Visão financeira de O.S (legacy) |
| financeiro_dashboard.html | /financeiro | financeiro | Dashboard financeiro com alertas |
| financeiro_ordens.html | /financeiro/ordens | financeiro | Aprovação de O.S + custos empresa + reabrir |
| financeiro_nova_os.html | /financeiro/nova-os | financeiro | Nova O.S pelo financeiro (aprovada automaticamente) |
| financeiro_prestacoes.html | /financeiro/prestacoes | financeiro | Análise de prestações de contas |
| financeiro_adiantamentos.html | /financeiro/adiantamentos | financeiro | Adiantamentos avulsos por colaborador |
| financeiro_contas.html | /financeiro/contas | financeiro | Contas a pagar e receber |
| financeiro_relatorios.html | /financeiro/relatorios | financeiro | Relatórios em PDF |
| colaborador_os.html | /colaborador/os | colaborador | App mobile-first — Minhas Viagens |

---

## 12. Rotas da API (main.py)

### 12.1 Autenticação
```
POST /login                       # Login com email + senha
GET  /logout                      # Limpa cookies e redireciona para /
POST /registrar                   # Registrar novo usuário
```

### 12.2 APIs Gerais
```
GET  /api/meu-email               # Retorna email e perfil do usuário logado
GET  /api/portal-stats            # Stats para os cards do portal
GET  /api/notificacoes            # Total de notificações pendentes
```

### 12.3 APIs Chamados
```
GET  /api/meus-chamados           # Lista chamados do usuário logado
POST /chamado                     # Abre novo chamado (multipart/form-data)
POST /chamado/{id}/complementar   # Envia complemento/mensagem
POST /chamado/{id}/fechar         # Marca como resolvido
POST /chamado/{id}/reabrir        # Reabre chamado fechado
GET  /api/chamados/{id}/mensagens # Mensagens do chamado
GET  /api/chamados/{id}/historico # Timeline de eventos
POST /admin/chamado/{id}/pedir-info      # Admin pede informações
POST /admin/chamado/{id}/resposta        # Admin registra resposta do parceiro
POST /admin/chamado/{id}/vincular-qualitor # Vincula ID Qualitor
POST /admin/chamado/{id}/editar          # Edita chamado
POST /admin/chamado/{id}/adicionar-participante
GET  /api/relatorio-semanal-cron?chave=suporte2024cron # Relatório semanal
```

### 12.4 APIs Ordens de Serviço
```
GET/POST   /api/os/departamentos
GET/POST   /api/os/municipios
GET/POST   /api/os/tipos-transporte
GET/POST   /api/os/tipos-adiantamento
GET/POST   /api/os/sequencia
GET        /api/os/proximo-numero          # Incrementa e retorna próximo número
GET        /api/os/proximo-numero-preview  # Retorna sem incrementar
GET        /api/os/colaboradores           # Lista perfis ativos
GET/POST   /api/os/ordens                  # Lista (?meu=1 filtra por e-mail) / Cria
GET        /api/os/ordens/{id}             # Detalhes de uma O.S
POST       /api/os/ordens/{id}/aprovar     # Aprova O.S + envia e-mail
POST       /api/os/ordens/{id}/cancelar    # Cancela O.S
POST       /api/os/ordens/{id}/encerrar    # Encerra O.S
POST       /api/os/ordens/{id}/reabrir     # Reabre O.S (volta para "aprovada")
GET/POST   /api/os/ordens/{id}/prestacao   # Lista / Cria item de prestação
POST       /api/os/ordens/{id}/prestacao/anexos  # Upload múltiplos anexos
GET/POST   /api/os/ordens/{id}/custos-empresa    # Custos da empresa
DELETE     /api/os/custos-empresa/{id}           # Remove custo
POST       /api/os/prestacao/{id}/aprovar  # Aprova item + e-mail
POST       /api/os/prestacao/{id}/devolver # Devolve item + e-mail
GET        /os/ordens/{id}/pdf             # PDF da O.S via WeasyPrint
```

### 12.5 APIs Financeiro
```
GET/POST/DELETE  /api/financeiro/adiantamentos       # Adiantamentos avulsos
GET/POST/DELETE  /api/financeiro/contas              # Contas a pagar/receber
POST             /api/financeiro/contas/{id}/pagar   # Marca conta como paga
GET              /api/financeiro/dashboard           # Dados do dashboard
POST             /api/financeiro/relatorio-pdf       # Gera relatório em PDF
```

---

## 13. Fluxos de Status

### 13.1 Ordens de Serviço

```
emitida
  └─► aprovada (financeiro aprova ou emite direto como aprovada)
        └─► prestacao_enviada (colaborador envia prestação)
              ├─► prestacao_devolvida (financeiro devolve para correção)
              │     └─► prestacao_enviada (colaborador corrige e reenvio)
              └─► prestacao_aprovada (todas as prestações aprovadas)
                    └─► encerrada (financeiro encerra)

cancelada ◄─ qualquer etapa (financeiro cancela)
aprovada  ◄─ encerrada/cancelada/prestacao_aprovada (financeiro reabre)
```

**Regra de prestacao_aprovada:** O sistema verifica se TODAS as prestações da O.S estão aprovadas. Se sim, status vai para `prestacao_aprovada`. Se ainda há pendentes, fica em `prestacao_enviada`.

### 13.2 Chamados

```
aberto
  └─► em_analise (admin vincula Qualitor)
        ├─► aguardando_colaborador (admin pede informações)
        │     └─► em_analise (colaborador complementa)
        └─► pendente_dev (admin registra resposta do parceiro)
              └─► fechado (colaborador ou admin fecha)

fechado → reaberto → em_analise
```

---

## 14. Como o Frontend Chama a API

### Upload com barra de progresso (XHR)
Usado em `formulario.html` para uploads grandes:

```javascript
const xhr = new XMLHttpRequest();
xhr.upload.addEventListener('progress', function(e) {
    if (e.lengthComputable) {
        const pct = Math.round((e.loaded / e.total) * 100);
        // Atualiza barra de progresso
    }
});
xhr.addEventListener('load', function() {
    if (xhr.status >= 200 && xhr.status < 300) {
        const data = JSON.parse(xhr.responseText);
        // Sucesso
    }
});
xhr.timeout = 300000; // 5 minutos
xhr.open('POST', '/chamado');
xhr.send(formData);
```

### Fetch padrão (demais chamadas)
```javascript
const res = await fetch('/api/os/ordens', {
    method: 'POST',
    body: form  // FormData ou JSON
});
const data = await res.json();
```

### Múltiplos arquivos selecionados
O formulário mantém array de arquivos em memória:
```javascript
let arquivosSelecionados = [];

function selecionarArquivo(input) {
    const novos = Array.from(input.files);
    arquivosSelecionados = [...arquivosSelecionados, ...novos];
    renderPreview();
    input.value = ''; // Limpa input para permitir selecionar de novo
}
```

### Filtro de O.S do colaborador
```javascript
// Busca apenas as O.S do usuário logado
fetch('/api/os/ordens?meu=1')
```

---

## 15. E-mail (Resend)

**Remetente:** `Inovatus Sistemas <noreply@voosuporte.com.br>`
**Domínio:** voosuporte.com.br verificado com DKIM, SPF, MX, DMARC na Hostinger

### Eventos e destinatários

| Evento | Destinatário |
|--------|-------------|
| Novo chamado aberto | Todos os admins |
| Admin pede informações | Colaborador do chamado + participantes |
| Admin registra resposta do parceiro | Colaborador do chamado + participantes |
| Usuário adicionado a chamado | Novo participante |
| O.S emitida | Colaborador da O.S |
| O.S aprovada pelo financeiro | Colaborador da O.S |
| Prestação aprovada | Colaborador da O.S |
| Prestação devolvida | Colaborador da O.S |

### Como enviar e-mail no código
```python
import resend
resend.api_key = RESEND_KEY

resend.Emails.send({
    "from": "Inovatus Sistemas <noreply@voosuporte.com.br>",
    "to": destinatario,
    "subject": "Assunto aqui",
    "html": "<p>Corpo do e-mail em HTML</p>"
})
```

---

## 16. Como Rodar Localmente

### Pré-requisitos
- Python 3.12+
- pip
- WeasyPrint e suas dependências nativas (libcairo, pango, etc.)

### Passos

```bash
# 1. Clonar repositório
git clone https://github.com/Jocirio/suporte-chamados.git
cd suporte-chamados

# 2. Criar e ativar ambiente virtual
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 3. Instalar dependências
pip install -r requirements.txt

# 4. Criar arquivo .env com as credenciais
cp .env.example .env   # Se existir
# Editar .env com os valores corretos

# 5. Criar pasta de uploads
mkdir -p static/uploads

# 6. Rodar o servidor
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 7. Acessar em http://localhost:8000
```

> **Atenção:** Em desenvolvimento local, os arquivos ficam em `./static/uploads/` e URLs de produção (`https://voosuporte.com.br/static/uploads/`) não vão funcionar. Ajuste a função `fazer_upload()` para usar URL local.

---

## 17. Manutenção e Comandos

### Atualizar o sistema
```bash
/root/suporte-chamados/atualizar.sh
# Equivalente a:
cd /root/suporte-chamados && git pull && systemctl restart suporte
```

### Comandos úteis
```bash
# Ver logs em tempo real
journalctl -u suporte -f

# Ver últimos 50 logs
journalctl -u suporte -n 50 --no-pager

# Validar sintaxe do main.py antes de reiniciar
cd /root/suporte-chamados && venv/bin/python3 -c "import main"

# Recarregar Nginx após alterações
nginx -t && systemctl reload nginx

# Ver configuração Nginx atual
cat /etc/nginx/sites-enabled/voosuporte.com.br

# Git divergente (quando há commits locais e remotos)
git config pull.rebase false && git pull

# Renovar SSL (automático via certbot, mas manual se necessário)
certbot renew

# Permissões da pasta de uploads
chmod 755 /root/suporte-chamados/static/uploads/
chmod 644 /root/suporte-chamados/static/uploads/*

# Ver espaço em disco
df -h /root
du -sh /root/suporte-chamados/static/uploads/
```

### GitHub — Configurar token de acesso
```bash
# Configurar token PAT (Personal Access Token) para push
git remote set-url origin https://jocirio:TOKEN@github.com/Jocirio/suporte-chamados.git

# Após uso, revogar em:
# github.com > Settings > Developer settings > Personal access tokens
```

---

## 18. SQL Importantes Aplicados no Supabase

Os comandos abaixo foram executados no **SQL Editor** do Supabase durante o desenvolvimento:

```sql
-- Desabilitar RLS nas tabelas financeiras (necessário para acesso via chave anon)
ALTER TABLE os_adiantamentos_avulsos DISABLE ROW LEVEL SECURITY;
ALTER TABLE financeiro_contas DISABLE ROW LEVEL SECURITY;
ALTER TABLE os_custos_empresa DISABLE ROW LEVEL SECURITY;

-- Aumentar limite do bucket de storage para 500MB
UPDATE storage.buckets
SET file_size_limit = 524288000
WHERE id = 'evidencias';

-- Verificar limite atual do bucket
SELECT id, file_size_limit FROM storage.buckets WHERE id = 'evidencias';

-- Verificar se coluna comprovante_urls existe na prestacao_contas
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'os_prestacao_contas';

-- Adicionar coluna se não existir
ALTER TABLE os_prestacao_contas
ADD COLUMN IF NOT EXISTS comprovante_urls JSONB DEFAULT '[]';
```

---

## 19. Problemas Comuns e Soluções

| Problema | Causa | Solução |
|---------|-------|---------|
| Erro 500 em /api/meu-email | Token JWT expirado | Usuário faz logout e login novamente |
| PDF abre como código binário | Content-Type incorreto ou arquivo no Supabase (antigo) | Verificar `location /static/uploads/` no Nginx + permissões |
| Upload retorna 413 | Arquivo maior que limite do Nginx | Verificar `client_max_body_size 500M` no Nginx |
| Upload retorna 504 | Timeout no processamento | Verificar `proxy_read_timeout 300` no Nginx e `--timeout-keep-alive 300` no Uvicorn |
| Upload salva mas Supabase retorna 413 | Limite do plano gratuito (50MB) | A função `fazer_upload()` atual já usa servidor local — não chama o Supabase |
| IndentationError no Python | Espaçamento incorreto no main.py | `venv/bin/python3 -c "import main"` para localizar |
| Git pull falha (divergent branches) | Commits locais divergem do remoto | `git config pull.rebase false && git pull` |
| RLS error no Supabase | Row Level Security bloqueando acesso | `ALTER TABLE nome DISABLE ROW LEVEL SECURITY` |
| Serviço não inicia após atualização | Erro no main.py | `journalctl -u suporte -n 30 --no-pager` para ver o erro |
| Nginx 403 Forbidden em /static/uploads/ | Permissão negada | `chmod 755 /root && chmod 755 static/uploads/` |
| E-mail não chega | RESEND_KEY inválida ou domínio não verificado | Verificar .env e dashboard do Resend |
| O.S não incrementa número | Tabela os_sequencia sem registro para o ano | Inserir: `INSERT INTO os_sequencia (ano, ultimo_numero) VALUES (2026, 0)` |

---

## 20. Pendências e Melhorias Futuras

| Item | Prioridade | Detalhes |
|------|-----------|---------|
| PDF de evidências antigas no Supabase | Alta | Arquivos enviados antes da mudança estão no Supabase com Content-Type errado. Novos uploads já funcionam corretamente |
| Múltiplos anexos na aba Detalhes | Média | O backend salva o 1º arquivo em `evidencia_url` e os demais em mensagens separadas. A aba Detalhes precisa buscar todas as mensagens de tipo `abertura` para listar todos os anexos |
| Token refresh automático | Média | Tokens Supabase expiram após algumas horas. Implementar refresh automático no frontend usando o `refresh_token` |
| Upload de foto pela câmera mobile | Média | POST chega ao servidor mas foto pode não salvar corretamente. Investigar a referência do arquivo após captura em `selecionarArquivos()` |
| PWA — App instalável | Baixa | Adicionar `manifest.json` + `service-worker.js` para instalação como app |
| Notificações push mobile | Baixa | Usar Web Push API + service worker |
| Backup automático do banco | Baixa | Configurar `pg_dump` agendado via cron no VPS |
| Sincronização GitHub | Info | Token PAT precisa ser reconfigurado quando expirar. Criar novo token em github.com > Settings > Developer settings |

---

## RESUMO RÁPIDO PARA PROGRAMADOR

**Para fazer uma alteração:**
1. Edite os arquivos no GitHub diretamente ou faça `git pull` + edite + `git push`
2. No servidor: `/root/suporte-chamados/atualizar.sh`
3. Se der erro: `journalctl -u suporte -n 20 --no-pager`

**Arquivo mais importante:** `main.py` — contém todas as rotas, lógica de negócio, chamadas ao Supabase e envio de e-mails.

**Para adicionar nova rota:**
```python
@app.get("/minha-rota", response_class=HTMLResponse)
async def minha_rota(request: Request):
    token = request.cookies.get("token")
    if not token:
        return RedirectResponse(url="/")
    # Verificar módulo se necessário
    return templates.TemplateResponse(request=request, name="meu_template.html")
```

**Para consultar o banco:**
```python
resultado = supabase.table("nome_tabela").select("*").eq("coluna", valor).execute()
dados = resultado.data  # Lista de dicionários
```

---

*Documentação gerada em Abril/2026 — Inovatus Sistemas*
*Contato: jocirioarruda@gmail.com*
