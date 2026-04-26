[Documentacao_Complementar_Inovatus.md](https://github.com/user-attachments/files/27102472/Documentacao_Complementar_Inovatus.md)
# DOCUMENTAÇÃO COMPLEMENTAR — Inovatus Sistemas
**Estrutura do main.py | Schema do Banco | WeasyPrint | E-mails | CSS | Cron | SSL**
**Abril/2026**

---

## ÍNDICE
1. Estrutura do main.py
2. Schema do Banco de Dados (detalhado)
3. Geração de PDF com WeasyPrint
4. Templates de E-mail (HTML)
5. Padrões de Erro da API
6. Referência de Classes CSS
7. Relatório Semanal (Cron)
8. SSL — Renovação e Manutenção

---

## 1. ESTRUTURA DO main.py

O arquivo `main.py` é o único arquivo Python do projeto. Toda a lógica está nele.
Está organizado em seções comentadas na seguinte ordem:

```python
# ============================================================
# IMPORTS E CONFIGURAÇÃO
# ============================================================
from fastapi import FastAPI, Request, Form, File, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from supabase import create_client
from dotenv import load_dotenv
import os, resend, json
from datetime import datetime, timezone
from weasyprint import HTML as WeasyHTML

load_dotenv()

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Clientes Supabase
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
supabase_admin = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

resend.api_key = RESEND_KEY

# ============================================================
# FUNÇÃO DE UPLOAD
# ============================================================
async def fazer_upload(arquivo: UploadFile) -> str:
    # Salva em /static/uploads/ e retorna URL pública

# ============================================================
# FUNÇÕES AUXILIARES DE E-MAIL
# ============================================================
def enviar_email_novo_chamado(chamado)
def enviar_email_pedido_info(chamado, mensagem, destinatarios)
def enviar_email_resposta_parceiro(chamado, mensagem, destinatarios)
def enviar_email_os_emitida(os_data, colaborador_email)
def enviar_email_os_aprovada(os_data, colaborador_email)
def enviar_email_prestacao_aprovada(prestacao, os_numero, colaborador_email)
def enviar_email_prestacao_devolvida(prestacao, os_numero, colaborador_email, motivo)

# ============================================================
# ROTAS DE PÁGINAS (HTML)
# ============================================================
# GET /                     → login.html
# GET /portal               → portal.html
# GET /configuracoes        → configuracoes_gerais.html
# GET /admin                → dashboard.html
# ... (todos os templates)

# ============================================================
# AUTENTICAÇÃO
# ============================================================
# POST /login
# GET  /logout
# POST /registrar

# ============================================================
# APIs GERAIS
# ============================================================
# GET /api/meu-email
# GET /api/portal-stats
# GET /api/notificacoes

# ============================================================
# MÓDULO CHAMADOS
# ============================================================
# GET  /api/meus-chamados
# GET  /api/chamados-todos
# POST /chamado
# POST /chamado/{id}/complementar
# POST /chamado/{id}/fechar
# POST /chamado/{id}/reabrir
# GET  /api/chamados/{id}/mensagens
# GET  /api/chamados/{id}/historico
# POST /admin/chamado/{id}/pedir-info
# POST /admin/chamado/{id}/resposta
# POST /admin/chamado/{id}/vincular-qualitor
# POST /admin/chamado/{id}/editar
# POST /admin/chamado/{id}/adicionar-participante
# GET  /api/relatorio-semanal-cron

# ============================================================
# MÓDULO ORDENS DE SERVIÇO
# ============================================================
# GET/POST /api/os/departamentos
# GET/POST /api/os/municipios
# ... (todas as rotas de O.S)

# ============================================================
# MÓDULO FINANCEIRO
# ============================================================
# GET/POST/DELETE /api/financeiro/adiantamentos
# ... (todas as rotas financeiro)
```

### Padrão de uma rota GET de página

```python
@app.get("/financeiro", response_class=HTMLResponse)
async def financeiro_dashboard(request: Request):
    token = request.cookies.get("token")
    if not token:
        return RedirectResponse(url="/")
    try:
        user = supabase.auth.get_user(token)
    except:
        return RedirectResponse(url="/")
    perfil = supabase.table("perfis").select("modulos, role").eq("email", user.user.email).execute()
    if not perfil.data:
        return RedirectResponse(url="/")
    modulos = perfil.data[0].get("modulos") or []
    if "financeiro" not in modulos and perfil.data[0].get("role") != "admin":
        return RedirectResponse(url="/portal")
    return templates.TemplateResponse(request=request, name="financeiro_dashboard.html")
```

### Padrão de uma rota GET de API

```python
@app.get("/api/os/ordens")
async def listar_ordens(request: Request):
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=401)
    user = supabase.auth.get_user(token)
    meu = request.query_params.get("meu")

    query = supabase.table("os_ordens").select("*, os_departamentos(nome)")
    if meu:
        query = query.eq("colaborador_email", user.user.email)
    query = query.order("created_at", desc=True)

    resultado = query.execute()
    return resultado.data
```

### Padrão de uma rota POST de API

```python
@app.post("/api/os/ordens/{id}/aprovar")
async def aprovar_ordem(id: str, request: Request):
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=401)
    user = supabase.auth.get_user(token)

    # Atualizar status
    supabase.table("os_ordens").update({
        "status": "aprovada",
        "aprovado_por": user.user.email,
        "aprovado_em": datetime.now(timezone.utc).isoformat()
    }).eq("id", id).execute()

    # Buscar dados para e-mail
    os_data = supabase.table("os_ordens").select("*").eq("id", id).execute()
    if os_data.data:
        try:
            enviar_email_os_aprovada(os_data.data[0], os_data.data[0]["colaborador_email"])
        except Exception as e:
            print(f"Erro e-mail: {e}")

    return {"status": "aprovada"}
```

### Padrão de upload multipart

```python
@app.post("/chamado")
async def novo_chamado(
    request: Request,
    colaborador_email: str = Form(...),
    unidade: str = Form(...),
    cliente_nome: str = Form(...),
    descricao_tecnica: str = Form(...),
    categoria: str = Form(...),
    prioridade: str = Form(...),
    link_url: str = Form(""),
    arquivos: list[UploadFile] = File(...)
):
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=401)

    # Upload de todos os arquivos
    urls = []
    for arq in arquivos:
        if arq.filename:
            url = await fazer_upload(arq)
            if url:
                urls.append(url)

    # Salvar no banco
    chamado = supabase.table("chamados_controle").insert({...}).execute()

    # Salvar mensagem de abertura com primeiro arquivo
    supabase.table("chamados_mensagens").insert({
        "chamado_id": chamado.data[0]["id"],
        "tipo": "abertura",
        "mensagem": descricao_tecnica,
        "evidencia_url": urls[0] if urls else None
    }).execute()

    # Salvar mensagens extras para os demais arquivos
    for url in urls[1:]:
        supabase.table("chamados_mensagens").insert({
            "chamado_id": chamado.data[0]["id"],
            "tipo": "abertura",
            "mensagem": "(arquivo adicional)",
            "evidencia_url": url
        }).execute()

    return {"id": chamado.data[0]["id"]}
```

---

## 2. SCHEMA DO BANCO DE DADOS (Detalhado)

### Tabela: perfis

```sql
CREATE TABLE perfis (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email       TEXT UNIQUE NOT NULL,
    nome        TEXT,
    role        TEXT DEFAULT 'colaborador',  -- 'admin' | 'colaborador'
    modulos     JSONB DEFAULT '[]',           -- array: ['chamados','ordens_servico','financeiro','colaborador']
    cargo       TEXT,
    departamento_id UUID REFERENCES os_departamentos(id),
    ativo       BOOLEAN DEFAULT true,
    created_at  TIMESTAMPTZ DEFAULT now()
);
```

### Tabela: clientes

```sql
CREATE TABLE clientes (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nome         TEXT NOT NULL,         -- Nome do município
    uf           TEXT,                  -- Ex: 'CE', 'SP'
    distancia_km NUMERIC,               -- Distância em KM (só ida)
    created_at   TIMESTAMPTZ DEFAULT now()
);
-- ATENÇÃO: Esta tabela é usada também como "municípios" no módulo O.S
```

### Tabela: chamados_controle

```sql
CREATE TABLE chamados_controle (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    colaborador_email TEXT NOT NULL,
    cliente_nome      TEXT,             -- Nome do município
    unidade           TEXT,             -- Nome da unidade de saúde
    descricao_tecnica TEXT,
    status            TEXT DEFAULT 'aberto',
    -- Valores: aberto | em_analise | aguardando_colaborador | pendente_dev | fechado
    prioridade        TEXT DEFAULT 'media',
    -- Valores: baixa | media | alta | urgente
    categoria         TEXT DEFAULT 'outro',
    -- Valores: erro_sistema | acesso | lentidao | duvida | implantacao | outro
    qualitor_id       TEXT,             -- ID no sistema Qualitor (externo)
    sla_horas         INTEGER DEFAULT 48,
    evidencia_url     TEXT,             -- URL do primeiro anexo
    link_url          TEXT,             -- URL do sistema com problema
    ultima_interacao  TIMESTAMPTZ DEFAULT now(),
    created_at        TIMESTAMPTZ DEFAULT now()
);
```

### Tabela: chamados_mensagens

```sql
CREATE TABLE chamados_mensagens (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chamado_id  UUID REFERENCES chamados_controle(id),
    tipo        TEXT,
    -- Valores: abertura | pedido_info | resposta | complemento
    mensagem    TEXT,
    evidencia_url TEXT,                 -- URL do arquivo anexado
    created_at  TIMESTAMPTZ DEFAULT now()
);
-- NOTA: múltiplos arquivos → múltiplas mensagens do mesmo tipo 'abertura'
```

### Tabela: chamados_historico

```sql
CREATE TABLE chamados_historico (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chamado_id  UUID REFERENCES chamados_controle(id),
    evento      TEXT,
    -- Valores: aberto | qualitor_vinculado | pedido_info | complementado |
    --          resposta_recebida | editado | reaberto | fechado | participante_adicionado
    descricao   TEXT,
    autor       TEXT,                   -- E-mail de quem gerou o evento
    created_at  TIMESTAMPTZ DEFAULT now()
);
```

### Tabela: chamados_participantes

```sql
CREATE TABLE chamados_participantes (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chamado_id  UUID REFERENCES chamados_controle(id),
    email       TEXT NOT NULL,
    added_at    TIMESTAMPTZ DEFAULT now()
);
```

### Tabela: os_departamentos

```sql
CREATE TABLE os_departamentos (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nome            TEXT NOT NULL,
    valor_diaria    NUMERIC NOT NULL DEFAULT 0,
    valor_meia_diaria NUMERIC NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ DEFAULT now()
);
```

### Tabela: os_ordens

```sql
CREATE TABLE os_ordens (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    numero            TEXT,             -- Ex: '001/2026'
    colaborador_email TEXT NOT NULL,
    colaborador_nome  TEXT,
    departamento_id   UUID REFERENCES os_departamentos(id),
    municipio_id      UUID REFERENCES clientes(id),
    municipio_nome    TEXT,
    data_saida        DATE,
    data_retorno      DATE,
    dias              INTEGER,          -- Calculado automaticamente
    diarias           NUMERIC,          -- Valor total das diárias
    meia_diaria       BOOLEAN DEFAULT false,
    valor_total       NUMERIC,          -- diarias + adiantamentos
    status            TEXT DEFAULT 'emitida',
    -- Valores: emitida | aprovada | prestacao_enviada | prestacao_devolvida |
    --          prestacao_aprovada | encerrada | cancelada
    adiantamentos     JSONB DEFAULT '[]',
    -- Array de objetos: [{"tipo": "combustível", "valor": 100}, ...]
    tipo_transporte   TEXT,
    observacoes       TEXT,
    aprovado_por      TEXT,
    aprovado_em       TIMESTAMPTZ,
    created_at        TIMESTAMPTZ DEFAULT now()
);
```

### Tabela: os_prestacao_contas

```sql
CREATE TABLE os_prestacao_contas (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    os_id             UUID REFERENCES os_ordens(id),
    colaborador_email TEXT,
    tipo              TEXT,             -- Ex: 'alimentação', 'combustível', 'hospedagem'
    descricao         TEXT,
    valor             NUMERIC,
    status            TEXT DEFAULT 'pendente',
    -- Valores: pendente | aprovado | devolvido
    comprovante_urls  JSONB DEFAULT '[]',
    -- Array de URLs: ["https://voosuporte.com.br/static/uploads/abc.jpg", ...]
    motivo_devolucao  TEXT,
    aprovado_por      TEXT,
    aprovado_em       TIMESTAMPTZ,
    created_at        TIMESTAMPTZ DEFAULT now()
);
```

### Tabela: os_custos_empresa

```sql
CREATE TABLE os_custos_empresa (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    os_id       UUID REFERENCES os_ordens(id),
    tipo        TEXT,                   -- Ex: 'hotel', 'passagem aérea'
    descricao   TEXT,
    valor       NUMERIC,
    created_at  TIMESTAMPTZ DEFAULT now()
);
-- RLS: DESABILITADO
```

### Tabela: os_sequencia

```sql
CREATE TABLE os_sequencia (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ano           INTEGER UNIQUE NOT NULL,  -- Ex: 2026
    ultimo_numero INTEGER DEFAULT 0
);
-- Inserir para cada ano: INSERT INTO os_sequencia (ano, ultimo_numero) VALUES (2026, 0);
```

### Tabela: os_adiantamentos_avulsos

```sql
CREATE TABLE os_adiantamentos_avulsos (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    colaborador_email TEXT NOT NULL,
    valor             NUMERIC NOT NULL,
    descricao         TEXT,
    data              DATE,
    created_at        TIMESTAMPTZ DEFAULT now()
);
-- RLS: DESABILITADO
```

### Tabela: financeiro_contas

```sql
CREATE TABLE financeiro_contas (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tipo        TEXT NOT NULL,          -- 'pagar' | 'receber'
    descricao   TEXT NOT NULL,
    valor       NUMERIC NOT NULL,
    vencimento  DATE,
    status      TEXT DEFAULT 'pendente', -- 'pendente' | 'pago'
    pago_em     TIMESTAMPTZ,
    created_at  TIMESTAMPTZ DEFAULT now()
);
-- RLS: DESABILITADO
```

---

## 3. GERAÇÃO DE PDF COM WEASYPRINT

### Como funciona

O WeasyPrint converte HTML+CSS em PDF no servidor. É usado para:
- PDF da Ordem de Serviço (`GET /os/ordens/{id}/pdf`)
- Relatórios financeiros (`POST /api/financeiro/relatorio-pdf`)

### Rota do PDF da O.S

```python
@app.get("/os/ordens/{id}/pdf")
async def pdf_ordem(id: str, request: Request):
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=401)

    # Buscar dados da O.S com joins
    os_data = supabase.table("os_ordens").select(
        "*, os_departamentos(nome, valor_diaria, valor_meia_diaria)"
    ).eq("id", id).execute()

    if not os_data.data:
        raise HTTPException(status_code=404)

    os_obj = os_data.data[0]

    # Montar HTML do PDF
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: Arial, sans-serif; font-size: 12px; }}
            .header {{ text-align: center; border-bottom: 2px solid #333; padding-bottom: 12px; }}
            .titulo {{ font-size: 20px; font-weight: bold; }}
            .numero {{ font-size: 14px; color: #666; }}
            .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin: 16px 0; }}
            .campo label {{ font-size: 10px; color: #888; text-transform: uppercase; display: block; }}
            .campo span {{ font-size: 13px; font-weight: 500; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 16px; }}
            th {{ background: #333; color: #fff; padding: 8px; text-align: left; font-size: 11px; }}
            td {{ padding: 8px; border-bottom: 1px solid #eee; font-size: 12px; }}
            .total {{ font-weight: bold; font-size: 14px; text-align: right; margin-top: 16px; }}
            .assinatura {{ margin-top: 48px; display: grid; grid-template-columns: 1fr 1fr; gap: 40px; }}
            .ass-linha {{ border-top: 1px solid #333; padding-top: 8px; text-align: center; font-size: 11px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <div class="titulo">ORDEM DE SERVIÇO</div>
            <div class="numero">Nº {os_obj['numero']}</div>
        </div>
        <div class="grid">
            <div class="campo"><label>Colaborador</label><span>{os_obj['colaborador_nome']}</span></div>
            <div class="campo"><label>Departamento</label><span>{os_obj.get('os_departamentos', {}).get('nome', '—')}</span></div>
            <div class="campo"><label>Município</label><span>{os_obj['municipio_nome']}</span></div>
            <div class="campo"><label>Período</label><span>{os_obj['data_saida']} a {os_obj['data_retorno']}</span></div>
            <div class="campo"><label>Dias</label><span>{os_obj['dias']}</span></div>
            <div class="campo"><label>Status</label><span>{os_obj['status'].upper()}</span></div>
        </div>
        <!-- adiantamentos, total, assinaturas -->
    </body>
    </html>
    """

    # Gerar PDF com WeasyPrint
    pdf_bytes = WeasyHTML(string=html_content).write_pdf()

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename=OS_{os_obj['numero'].replace('/', '-')}.pdf"}
    )
```

### Instalação do WeasyPrint (dependências nativas)

```bash
# Ubuntu/Debian (necessário no servidor e no desenvolvimento)
apt-get install -y libcairo2 libpango-1.0-0 libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 libffi-dev shared-mime-info

# Python
pip install weasyprint
```

---

## 4. TEMPLATES DE E-MAIL (HTML)

Todos os e-mails usam o padrão abaixo. O HTML é inline (sem arquivos separados — está direto no main.py).

### Padrão base de todos os e-mails

```html
<div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:24px;background:#fff">

  <!-- Header colorido -->
  <div style="background:#6366f1;color:#fff;padding:20px 24px;border-radius:10px 10px 0 0">
    <div style="font-size:18px;font-weight:700">Inovatus Sistemas</div>
    <div style="font-size:13px;opacity:.85">Sistema de Suporte Técnico</div>
  </div>

  <!-- Corpo -->
  <div style="border:1px solid #e5e7eb;border-top:none;padding:24px;border-radius:0 0 10px 10px">
    <h2 style="color:#111;margin-top:0">📋 Título do E-mail</h2>
    <p style="color:#374151;font-size:14px;line-height:1.6">Texto do e-mail aqui.</p>

    <!-- Tabela de informações -->
    <table style="width:100%;border-collapse:collapse;margin:16px 0">
      <tr>
        <td style="padding:8px 12px;background:#f9fafb;color:#6b7280;font-size:12px;width:140px">Campo</td>
        <td style="padding:8px 12px;font-size:13px">Valor</td>
      </tr>
    </table>

    <!-- Botão de ação -->
    <a href="https://voosuporte.com.br/portal"
       style="display:inline-block;background:#6366f1;color:#fff;padding:10px 20px;
              border-radius:8px;text-decoration:none;font-size:13px;font-weight:600;margin-top:8px">
      Ver no sistema →
    </a>
  </div>

  <!-- Rodapé -->
  <div style="text-align:center;margin-top:16px;font-size:11px;color:#9ca3af">
    Inovatus Sistemas · voosuporte.com.br · Este é um e-mail automático
  </div>

</div>
```

### E-mail: Novo Chamado (para admins)
```
Assunto: 🆕 Novo chamado — [Unidade] · [Prioridade]
Cor header: #6366f1 (indigo)
Conteúdo: colaborador, unidade, município, categoria, prioridade, descrição
Botão: "Ver chamado →" → https://voosuporte.com.br/admin
```

### E-mail: Pedido de Informações (para colaborador + participantes)
```
Assunto: 🟡 O suporte precisa de informações — Chamado #[ID]
Cor header: #d97706 (amber)
Conteúdo: texto do pedido, unidade, status
Botão: "Responder agora →" → https://voosuporte.com.br/meus-chamados
```

### E-mail: Resposta do Parceiro (para colaborador + participantes)
```
Assunto: ✅ Resposta recebida — Chamado #[ID]
Cor header: #059669 (green)
Conteúdo: texto da resposta, unidade
Botão: "Ver resposta →" → https://voosuporte.com.br/meus-chamados
```

### E-mail: O.S Emitida (para colaborador)
```
Assunto: 📋 Nova Ordem de Serviço emitida — O.S [NUMERO]
Cor header: #6366f1 (indigo)
Conteúdo: número, município, departamento, período, dias, valor diárias, adiantamentos, total
Aviso: "Aguarde a aprovação do financeiro antes de viajar."
Botão: "Ver minhas O.S →" → https://voosuporte.com.br/colaborador/os
```

### E-mail: O.S Aprovada (para colaborador)
```
Assunto: ✅ Ordem de Serviço aprovada — O.S [NUMERO]
Cor header: #059669 (green)
Conteúdo: número, município, período, valor total
Aviso: "Você já pode realizar a viagem."
Botão: "Ver minhas O.S →" → https://voosuporte.com.br/colaborador/os
```

### E-mail: Prestação Aprovada (para colaborador)
```
Assunto: ✅ Prestação de contas aprovada — O.S [NUMERO]
Cor header: #059669 (green)
Conteúdo: tipo, descrição, valor
Botão: "Ver minhas O.S →" → https://voosuporte.com.br/colaborador/os
```

### E-mail: Prestação Devolvida (para colaborador)
```
Assunto: ↩ Prestação devolvida para correção — O.S [NUMERO]
Cor header: #dc2626 (red)
Conteúdo: tipo, descrição, valor, motivo da devolução
Botão: "Corrigir e reenviar →" → https://voosuporte.com.br/colaborador/os
```

---

## 5. PADRÕES DE ERRO DA API

### Estrutura de respostas

```python
# Sucesso
return {"status": "ok"}
return {"status": "criado", "id": "uuid-aqui"}
return lista_de_dados  # Direto

# Erro de autenticação
raise HTTPException(status_code=401, detail="Não autenticado")

# Erro de autorização
raise HTTPException(status_code=403, detail="Sem permissão")

# Não encontrado
raise HTTPException(status_code=404, detail="Não encontrado")

# Erro do servidor (evitar expor detalhes)
raise HTTPException(status_code=500, detail="Erro interno")
```

### Como o frontend trata erros

```javascript
// Padrão usado nos templates
try {
    const res = await fetch('/api/...', { method: 'POST', body: form });
    if (res.status === 401) {
        window.location = '/';  // Redireciona para login
        return;
    }
    if (!res.ok) throw new Error('Erro ' + res.status);
    const data = await res.json();
    // Sucesso
} catch(e) {
    alert('Erro ao processar. Tente novamente.');
    console.error(e);
}
```

### Códigos de status usados

| Código | Situação |
|--------|---------|
| 200 | Sucesso |
| 201 | Criado com sucesso |
| 307 | Redirect (RedirectResponse) |
| 401 | Token ausente ou inválido |
| 403 | Usuário não tem permissão |
| 404 | Recurso não encontrado |
| 422 | Dados inválidos (FastAPI valida automaticamente) |
| 500 | Erro interno do servidor |

---

## 6. REFERÊNCIA DE CLASSES CSS

Classes reutilizáveis presentes em múltiplos templates:

### Layout

```css
.topbar          /* Barra superior sticky */
.logo            /* Logo com ponto colorido */
.logo-dot        /* Ponto indigo ao lado do logo */
.nav             /* Container de links de navegação */
.content         /* Área principal (max-width: 1000-1200px, margin: auto) */
.page-title      /* Título da página (font-size: 20px, font-weight: 600) */
```

### Cards e superfícies

```css
.table-card      /* Card com tabela (border-radius: 12px, sombra) */
.table-toolbar   /* Barra acima da tabela (busca + filtros) */
.modal-overlay   /* Fundo escuro do modal */
.modal           /* Container do modal (max-width: 640px) */
.modal-header    /* Header do modal */
.modal-body      /* Corpo do modal (overflow-y: auto) */
.modal-footer    /* Footer do modal */
.modal-tabs      /* Abas do modal */
.surface-card    /* Card genérico com border e sombra */
```

### Formulários

```css
.input           /* Input padrão */
.search-input    /* Input de busca com ícone */
.search-wrap     /* Container do input de busca */
.input-textarea  /* Textarea de mensagem */
.upload-zone     /* Área de drag & drop */
.upload-zone.tem-arquivo  /* Com arquivo selecionado */
.upload-zone.drag-over    /* Durante drag */
.progress-wrap   /* Container da barra de progresso */
.progress-bar-bg /* Fundo cinza da barra */
.progress-bar-fill /* Barra preenchida (largura animada via JS) */
```

### Botões

```css
.btn-primary    /* Botão principal (accent color) */
.btn-secondary  /* Botão secundário (transparente com borda) */
.btn-submit     /* Botão de envio do formulário */
.btn-enviar     /* Botão de enviar mensagem */
.btn-reabrir    /* Botão reabrir (azul outline) */
.btn-resolver   /* Botão marcar como resolvido */
.ver-btn        /* Botão "Ver" nas tabelas */
.theme-btn      /* Botão troca de tema */
.chip           /* Filtro de chip (pequeno, arredondado) */
.chip.active    /* Chip selecionado */
```

### Badges e indicadores

```css
.badge                    /* Badge base */
.badge.aberto             /* Azul */
.badge.em_analise         /* Roxo */
.badge.aguardando_colaborador  /* Âmbar */
.badge.pendente_dev       /* Verde */
.badge.fechado            /* Cinza */
.badge.pulso-aguard       /* Animação pulsante */

.pri-badge               /* Badge de prioridade */
.pri-badge.urgente       /* Roxo */
.pri-badge.alta          /* Vermelho */
.pri-badge.media         /* Âmbar */
.pri-badge.baixa         /* Verde */

.sla-badge               /* Badge de SLA */
.sla-badge.vencido       /* Vermelho */
.sla-badge.critico       /* Âmbar */
```

### Tabelas

```css
table            /* Tabela (width: 100%, border-collapse: collapse) */
th               /* Cabeçalho (fundo surface2, texto uppercase pequeno) */
td               /* Célula (border-bottom) */
tr:hover td      /* Hover na linha */
tr.aguardando td /* Linha com fundo âmbar (aguardando colaborador) */
tr.pri-urgente td /* Borda esquerda roxa */
tr.pri-alta td    /* Borda esquerda vermelha */
tr.pri-media td   /* Borda esquerda âmbar */
tr.pri-baixa td   /* Borda esquerda verde */
.id-col          /* Coluna de ID (monospace, texto pequeno) */
.count-info      /* Rodapé da tabela com contagem */
.empty-state     /* Estado vazio da tabela */
```

### Mensagens e conversa

```css
.conversa          /* Container de mensagens (flex column, gap) */
.msg-group         /* Grupo de mensagem (tag + bubble + meta) */
.msg-tag           /* Tag de tipo (pequena, uppercase) */
.msg-tag.interno   /* Azul */
.msg-tag.parceiro  /* Verde */
.msg-tag.colaborador /* Cinza */
.msg-tag.pedido    /* Âmbar */
.msg-bubble        /* Bolha da mensagem */
.msg-bubble.interno    /* Fundo azul claro, borda esquerda azul */
.msg-bubble.parceiro   /* Fundo verde claro, borda esquerda verde */
.msg-bubble.colaborador /* Fundo cinza, borda cinza */
.msg-bubble.pedido     /* Fundo âmbar, borda esquerda âmbar */
.msg-anexo         /* Container do anexo na mensagem */
.msg-meta          /* Metadados (data/hora, pequeno, cinza) */
```

### Timeline (Histórico)

```css
.timeline          /* Container da timeline */
.tl-item           /* Item da timeline */
.tl-dot            /* Ícone circular do evento */
.tl-connector      /* Linha vertical entre eventos */
.tl-evento         /* Título do evento */
.tl-desc           /* Descrição com fundo surface2 */
.tl-meta           /* Data e autor */
```

### Mobile (colaborador_os.html)

```css
.app               /* Container principal (100dvh, flex column) */
.main-content      /* Área scrollável */
.bottom-nav        /* Navegação inferior fixa */
.nav-btn           /* Botão da navegação */
.nav-btn.active    /* Botão ativo (accent color) */
.nav-icon          /* Ícone do botão */
.nav-label         /* Label do botão */
.tela-*            /* Telas individuais (dashboard, viagens, etc.) */
```

### Animações

```css
/* Pulsação para chamados aguardando resposta */
@keyframes pulso-aguard {
    0%, 100% { box-shadow: 0 0 0 0 rgba(202,138,4,.5); }
    50%       { box-shadow: 0 0 0 6px rgba(202,138,4,0); }
}
.badge.pulso-aguard { animation: pulso-aguard 1.8s ease-in-out infinite; }

/* Pulsação de fundo da linha */
@keyframes pulso-row-aguard {
    0%, 100% { background: transparent; }
    50%       { background: rgba(254,243,199,.6); }
}
tr.precisa-acao td { animation: pulso-row-aguard 2s ease-in-out infinite; }
```

### Alertas

```css
.alerta-box           /* Container de alerta (display:none por padrão) */
.alerta-box.show      /* Visível */
.alerta-box.amarelo   /* Fundo âmbar, ícone de info */
.alerta-box.vermelho  /* Fundo vermelho, ícone de alerta */
```

---

## 7. RELATÓRIO SEMANAL (Cron)

### Endpoint

```
GET /api/relatorio-semanal-cron?chave=suporte2024cron
```

A chave `suporte2024cron` é uma autenticação simples para que apenas o cron autorizado chame o endpoint.

### O que o relatório gera

```python
@app.get("/api/relatorio-semanal-cron")
async def relatorio_semanal(request: Request):
    chave = request.query_params.get("chave")
    if chave != "suporte2024cron":
        raise HTTPException(status_code=403)

    # Busca chamados abertos na última semana
    # Agrupa por status
    # Envia e-mail para todos os admins com resumo
    # Retorna {"status": "enviado"}
```

### O e-mail contém
- Total de chamados abertos
- Total aguardando resposta do colaborador
- Total com SLA vencido
- Lista de chamados urgentes/alta prioridade
- Novos chamados da semana

### Como agendar (cron no servidor)

```bash
# Editar crontab
crontab -e

# Adicionar linha (todo domingo às 8h)
0 8 * * 0 curl -s "https://voosuporte.com.br/api/relatorio-semanal-cron?chave=suporte2024cron" >> /var/log/relatorio-semanal.log 2>&1

# Verificar crontab ativo
crontab -l

# Ver log
cat /var/log/relatorio-semanal.log
```

---

## 8. SSL — RENOVAÇÃO E MANUTENÇÃO

### Certificado atual

| Item | Valor |
|------|-------|
| Provedor | Let's Encrypt (via Certbot) |
| Domínios | voosuporte.com.br e www.voosuporte.com.br |
| Validade | Até 24/07/2026 |
| Localização | /etc/letsencrypt/live/voosuporte.com.br/ |

### Arquivos do certificado

```
/etc/letsencrypt/live/voosuporte.com.br/
├── fullchain.pem   # Certificado completo (usado no Nginx)
├── privkey.pem     # Chave privada (usada no Nginx)
├── cert.pem        # Certificado sem cadeia
└── chain.pem       # Cadeia intermediária
```

### Renovação manual

```bash
# Verificar validade atual
certbot certificates

# Testar renovação (sem aplicar)
certbot renew --dry-run

# Renovar de verdade
certbot renew

# Recarregar Nginx após renovar
systemctl reload nginx
```

### Renovação automática

O Certbot instala automaticamente um timer systemd ou cron para renovação. Verificar:

```bash
# Ver timers do certbot
systemctl list-timers | grep certbot

# Ver cron do certbot
cat /etc/cron.d/certbot

# Status do timer
systemctl status certbot.timer
```

### Se o certificado expirar

```bash
# Parar Nginx temporariamente
systemctl stop nginx

# Renovar em modo standalone
certbot certonly --standalone -d voosuporte.com.br -d www.voosuporte.com.br

# Reiniciar Nginx
systemctl start nginx

# Verificar
certbot certificates
```

### Alerta antecipado

O Let's Encrypt envia e-mail automático para o endereço cadastrado (jocirioarruda@gmail.com) quando o certificado está próximo de vencer (30 dias antes).

---

## CHECKLIST DE ENTREGA PARA NOVO PROGRAMADOR

Antes de entregar o projeto para um novo programador, verificar:

- [ ] Acesso ao repositório GitHub concedido
- [ ] Credenciais do `.env` passadas de forma segura (não por e-mail)
- [ ] Acesso ao painel da Hostinger (VPS)
- [ ] Acesso ao painel do Supabase (projeto wvjsbgfnhdapqtinewgb)
- [ ] Acesso ao painel do Resend (para verificar e-mails)
- [ ] SSH configurado: `ssh root@187.127.28.178`
- [ ] Novo token PAT do GitHub configurado no servidor
- [ ] Documentação técnica completa entregue (3 arquivos .md)
- [ ] Walkthrough pelo sistema (demonstração ao vivo)

---

*Documentação Complementar — Abril/2026 — Inovatus Sistemas*
