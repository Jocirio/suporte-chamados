# GUIA COMPLETO DOS TEMPLATES HTML — Inovatus Sistemas

> Este documento descreve cada template HTML do sistema, suas seções, funções JavaScript, 
> elementos CSS e como se conectam à API. Use como mapa para se orientar no código.

---

## PADRÕES GLOBAIS (presentes em todos os templates)

### Tema Claro/Escuro
Todos os templates suportam dark mode via `data-theme="dark"` no `<html>`.

```javascript
// Presente em todos os templates
function initTheme() {
    const saved = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', saved);
    document.getElementById('theme-btn').textContent = saved === 'dark' ? '☀️' : '🌙';
}
function toggleTheme() {
    const c = document.documentElement.getAttribute('data-theme');
    const n = c === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', n);
    localStorage.setItem('theme', n);
}
```

### Variáveis CSS (CSS Custom Properties)
```css
:root {
    --bg: #f0f2f5;          /* Fundo da página */
    --surface: #fff;         /* Cards e modais */
    --surface2: #f9fafb;     /* Fundo alternativo */
    --border: #e5e7eb;       /* Bordas */
    --text: #111;            /* Texto principal */
    --text2: #6b7280;        /* Texto secundário */
    --text3: #9ca3af;        /* Texto terciário */
    --accent: #6366f1;       /* Cor de destaque (indigo) */
    --accent-hover: #4f46e5; /* Hover da cor de destaque */
    --shadow: 0 1px 3px rgba(0,0,0,.06);
}
[data-theme="dark"] {
    --bg: #0f1117;
    --surface: #1a1d27;
    --surface2: #141720;
    --border: #2d3148;
    --text: #f1f5f9;
    --text2: #94a3b8;
    --text3: #64748b;
    --accent: #818cf8;
    --accent-hover: #6366f1;
}
```

### Topbar (barra superior)
```html
<div class="topbar">
    <div class="logo"><div class="logo-dot"></div>Nome do Sistema</div>
    <div class="nav">
        <a href="/portal">⬅ Portal</a>
        <!-- links específicos de cada módulo -->
        <button class="theme-btn" onclick="toggleTheme()" id="theme-btn">🌙</button>
        <a href="/logout">Sair</a>
    </div>
</div>
```

---

## 1. login.html
**Rota:** `/`

### Estrutura
- Card centralizado com logo e formulário
- Campo email + senha
- Botão "Entrar"
- Link para /registrar

### JavaScript
```javascript
async function login() {
    const email = document.getElementById('email').value;
    const senha = document.getElementById('senha').value;
    const res = await fetch('/login', { method: 'POST', body: form });
    // Redireciona para /portal em caso de sucesso
}
```

### Observações
- Sem topbar (página pública)
- Mostra mensagem de erro inline se credenciais inválidas

---

## 2. registrar.html
**Rota:** `/registrar`

### Estrutura
- Formulário de cadastro
- Campos: nome, email, senha, confirmar senha

### Observações
- Após registro, redireciona para /portal
- Admin precisa depois configurar o perfil em /configuracoes

---

## 3. portal.html
**Rota:** `/portal`

### Estrutura
```
topbar
└── content
    ├── saudacao "Olá, [nome]!"
    ├── grid de cards (modulos-grid)
    │   ├── card Chamados (se módulo 'chamados' OU admin)
    │   ├── card Painel Admin (se role === 'admin')
    │   ├── card Ordens de Serviço (se módulo 'ordens_servico')
    │   ├── card Financeiro (se módulo 'financeiro')
    │   └── card Minhas Viagens (se módulo 'colaborador')
    └── rodapé
```

### JavaScript
```javascript
async function carregarPortal() {
    const perfil = await fetch('/api/meu-email').then(r => r.json());
    const stats  = await fetch('/api/portal-stats').then(r => r.json());
    // Monta HTML dos cards dinamicamente
    // Cada card exibe badges com contadores (ex: "3 pendentes")
}
```

### Cards e badges
- **Chamados:** badge amarelo (aguardando resposta) + badge vermelho (SLA vencido)
- **Admin:** badge com total de chamados abertos
- **O.S:** badge com O.S aguardando aprovação
- **Financeiro:** badge com pendências financeiras
- **Minhas Viagens:** badge com O.S pendentes + devolvidas

### Redirecionamento automático
```javascript
// Se usuário tem apenas 1 módulo, redireciona direto
if (unicoModulo === 'colaborador') window.location = '/colaborador/os';
if (unicoModulo === 'financeiro')  window.location = '/financeiro';
// Admin sempre vai para o portal
```

---

## 4. configuracoes_gerais.html
**Rota:** `/configuracoes`

### Estrutura
```
topbar (links: Portal, Chamados, Usuários)
└── content
    ├── tabs: Equipe | Municípios | Departamentos | Numeração O.S
    │
    ├── tab Equipe
    │   ├── tabela de usuários (nome, email, cargo, role, módulos)
    │   └── botão "+ Novo Usuário" → modal
    │
    ├── tab Municípios
    │   ├── tabela de municípios (nome, UF, distância KM)
    │   └── botão "+ Novo" → modal
    │
    ├── tab Departamentos
    │   ├── tabela de departamentos (nome, diária, meia-diária)
    │   └── botão "+ Novo" → modal
    │
    └── tab Numeração O.S
        ├── campo "Próximo número"
        └── botão "Salvar"
```

### Modal de perfil de usuário
```html
<!-- Checkboxes de módulos -->
<input type="checkbox" id="mod-chamados" value="chamados">
<input type="checkbox" id="mod-os" value="ordens_servico">
<input type="checkbox" id="mod-financeiro" value="financeiro">
<input type="checkbox" id="mod-colaborador" value="colaborador">
```

### JavaScript principal
```javascript
// Trocar abas
function mudarTab(tab) { ... }

// CRUD de cada seção
async function carregarEquipe()       { GET /api/perfis }
async function salvarUsuario()        { POST /api/perfis }
async function carregarMunicipios()   { GET /api/os/municipios }
async function salvarMunicipio()      { POST /api/os/municipios }
async function carregarDepartamentos(){ GET /api/os/departamentos }
async function salvarDepartamento()   { POST /api/os/departamentos }
async function salvarNumeracao()      { POST /api/os/sequencia }
```

---

## 5. formulario.html
**Rota:** `/novo-chamado`

### Estrutura
```
topbar (links: Portal, Meus Chamados)
└── content
    └── form-card
        ├── select Município (autocomplete)
        ├── input Unidade de Saúde
        ├── input URL do sistema (opcional)
        ├── radio Categoria (erro_sistema, acesso, lentidao, duvida, implantacao, outro)
        ├── radio Prioridade (baixa, media, alta, urgente)
        ├── textarea Descrição (mínimo 50 caracteres com contador)
        ├── upload-zone (drag & drop + clique)
        │   └── suporta: image/*, video/*, .pdf
        ├── progress-wrap (barra de progresso — aparece ao enviar)
        └── botão "Registrar chamado →"
```

### Array de arquivos múltiplos
```javascript
let arquivosSelecionados = [];  // Acumula arquivos sem substituir

function selecionarArquivo(input) {
    const novos = Array.from(input.files);
    arquivosSelecionados = [...arquivosSelecionados, ...novos];
    renderPreview();
    input.value = ''; // Limpa para permitir adicionar mais
}

function removerArquivoForm(i) {
    arquivosSelecionados.splice(i, 1);
    renderPreview();
}
```

### Envio com XHR e barra de progresso
```javascript
async function enviarChamado() {
    // Valida campos obrigatórios
    // Monta FormData com todos os arquivos
    arquivosSelecionados.forEach(arq => form.append('arquivos', arq));

    const xhr = new XMLHttpRequest();
    xhr.upload.addEventListener('progress', function(e) {
        if (e.lengthComputable) {
            const pct = Math.round((e.loaded / e.total) * 100);
            progressBar.style.width = pct + '%';
            progressText.innerHTML = pct + '% — ' + mbEnviado + ' MB de ' + mbTotal + ' MB';
        }
    });
    xhr.timeout = 300000; // 5 minutos
    xhr.open('POST', '/chamado');
    xhr.send(form);
}
```

### CSS classes importantes
```css
.upload-zone           /* Área de drag & drop */
.upload-zone.tem-arquivo  /* Estado com arquivo selecionado */
.upload-zone.drag-over    /* Estado durante drag */
.progress-wrap         /* Container da barra (display:none por padrão) */
.progress-wrap.show    /* Visível durante envio */
.progress-bar-fill     /* A barra em si (width animado via JS) */
.confirmacao           /* Card de confirmação (display:none) */
.confirmacao.show      /* Visível após envio bem-sucedido */
```

---

## 6. dashboard.html
**Rota:** `/admin`

### Estrutura
```
topbar (links: Portal, Novo Chamado, Meus Chamados, Configurações)
└── content
    ├── alertas (amarelo: aguardando resposta | vermelho: SLA vencido)
    ├── table-card
    │   ├── toolbar (busca + chips de filtro)
    │   ├── tabela (ID, Colaborador, Unidade, Descrição, Prioridade, Status, Data, Ações)
    │   └── count-info
    └── modal (overlay)
        ├── modal-header (ID, badges status e prioridade)
        ├── modal-tabs (Conversa | Detalhes | Histórico | Admin)
        ├── tab-conversa
        │   ├── legenda de cores
        │   ├── conversa-msgs (mensagens em thread)
        │   └── input-conversa (textarea + anexo)
        ├── tab-detalhes (campos do chamado)
        ├── tab-historico (timeline de eventos)
        ├── tab-admin (ferramentas do admin)
        │   ├── input Qualitor ID
        │   ├── select SLA
        │   ├── botão "Pedir informações"
        │   ├── textarea "Registrar resposta do parceiro"
        │   └── botão "Editar chamado"
        └── modal-footer (botões fechar, resolver)
```

### JavaScript principal
```javascript
let chamados = [];
let statusFiltro = 'ativos';
let prioFiltro = '';

async function carregar()          { GET /api/chamados-todos }
function aplicarFiltros()          { filtra chamados[] e renderiza tabela }
async function abrirModal(id)      { monta modal com dados do chamado }
async function carregarConversa(id){ GET /api/chamados/{id}/mensagens }
async function carregarTimeline(id){ GET /api/chamados/{id}/historico }
async function enviarMensagem()    { POST /admin/chamado/{id}/... }
async function pedirInfo()         { POST /admin/chamado/{id}/pedir-info }
async function registrarResposta() { POST /admin/chamado/{id}/resposta }
async function vincularQualitor()  { POST /admin/chamado/{id}/vincular-qualitor }
async function resolverChamado()   { POST /chamado/{id}/fechar }
```

### Tipos de mensagem e cores
```javascript
// Mapeamento tipo → classe CSS → label
abertura    → .colaborador   → "📤 Você · Abertura"
pedido_info → .pedido        → "🟡 Suporte · Pedido de informações"
resposta    → .parceiro      → "✅ Parceiro · Resposta recebida"
complemento → .colaborador   → "📝 Você · Complemento"
```

---

## 7. meus_chamados.html
**Rota:** `/meus-chamados`

### Estrutura
Idêntica ao `dashboard.html` mas:
- Busca apenas os chamados do colaborador logado (`GET /api/meus-chamados`)
- Tab "Admin" não existe no modal
- Colaborador pode: responder (complementar) e fechar chamado

### Diferenças do dashboard.html

```javascript
// No dashboard: todos os chamados
const res = await fetch('/api/chamados-todos');

// No meus_chamados: só os do usuário
const res = await fetch('/api/meus-chamados');
```

### Notificações em tempo real
```javascript
async function iniciarNotificacoes() {
    await Notification.requestPermission();
    setInterval(verificarNotificacoes, 30000); // A cada 30 segundos
}

async function verificarNotificacoes() {
    const data = await fetch('/api/notificacoes').then(r => r.json());
    // Mostra badge na navbar com total
    // Dispara notificação do sistema (push)
}
```

---

## 8. clientes.html
**Rota:** `/admin/clientes`

### Estrutura
```
topbar
└── content
    ├── tabela de clientes (nome, UF, distância)
    ├── botão "+ Novo"
    └── modal CRUD
        ├── input Nome (município)
        ├── input UF
        └── input Distância KM
```

---

## 9. usuarios.html
**Rota:** `/admin/usuarios`

### Estrutura
```
topbar
└── content
    ├── tabela de usuários
    └── modal de edição de perfil
        ├── campos pessoais (nome, cargo, departamento)
        ├── role (admin/colaborador)
        └── checkboxes de módulos
```

---

## 10. relatorios.html
**Rota:** `/relatorios`

### Estrutura
```
topbar
└── content
    ├── filtros (período, status, colaborador)
    ├── botão "Gerar relatório"
    └── tabela de resultados
```

---

## 11. os_dashboard.html
**Rota:** `/os`

### Estrutura
```
topbar (links: Portal, Nova O.S, Configurações)
└── content
    ├── cards de stats (total, aprovadas, em viagem, encerradas)
    ├── filtros (status, colaborador, período)
    ├── tabela de O.S
    │   └── colunas: Número, Colaborador, Município, Datas, Valor, Status, Ações
    └── modal de detalhes da O.S
        ├── header (número, status, badges)
        ├── tabs: Detalhes | Prestações | Custos
        ├── tab-detalhes
        │   ├── grid com todos os campos da O.S
        │   └── adiantamentos listados
        ├── tab-prestacoes
        │   └── lista de itens com status e comprovantes
        └── tab-custos
            └── lista de custos da empresa
```

### JavaScript principal
```javascript
async function carregar()           { GET /api/os/ordens }
async function abrirModal(id)       { GET /api/os/ordens/{id} }
async function carregarPrestacoes() { GET /api/os/ordens/{id}/prestacao }
async function carregarCustos()     { GET /api/os/ordens/{id}/custos-empresa }
async function gerarPDF(id)         { window.open('/os/ordens/{id}/pdf') }
```

---

## 12. os_nova.html
**Rota:** `/os/nova`

### Estrutura
```
topbar
└── content
    └── form-card
        ├── select Colaborador (busca perfis)
        ├── select Município
        ├── select Departamento (carrega valor da diária)
        ├── select Tipo de Transporte
        ├── date Data de Saída
        ├── date Data de Retorno
        ├── checkbox Meia-diária (saída/retorno)
        ├── resumo automático (dias calculados, valor)
        ├── seção Adiantamentos (dinâmica, múltiplos)
        │   └── [+ Adicionar adiantamento] → linha com tipo + valor
        └── botão "Emitir O.S"
```

### Cálculo automático
```javascript
function calcular() {
    const dias = calcularDias(saida, retorno);
    const meiaDiaria = document.getElementById('meia-diaria').checked;
    const diariaValor = parseFloat(departamento.dataset.diaria);
    const meiaValor = parseFloat(departamento.dataset.meia);
    
    let valor = dias * diariaValor;
    if (meiaDiaria) valor -= (diariaValor - meiaValor); // desconta 1 diária e adiciona meia
    // Exibe resumo
}
```

---

## 13. os_config.html
**Rota:** `/os/config`

### Estrutura
Configurações do módulo O.S:
- Departamentos (CRUD)
- Municípios (CRUD)
- Tipos de transporte (CRUD)
- Tipos de adiantamento (CRUD)
- Numeração sequencial (próximo número)

---

## 14. financeiro_dashboard.html
**Rota:** `/financeiro`

### Estrutura
```
topbar (links: Portal, Ordens, Prestações, Adiantamentos, Contas, Relatórios)
└── content
    ├── cards de alertas
    │   ├── O.S aguardando aprovação (vermelho se > 0)
    │   ├── Prestações para analisar (amarelo se > 0)
    │   ├── Contas vencendo em 7 dias (laranja se > 0)
    │   └── Adiantamentos em aberto
    ├── seção "O.S recentes" (últimas 5)
    └── seção "Contas próximas do vencimento"
```

### JavaScript principal
```javascript
async function carregarDashboard() {
    const data = await fetch('/api/financeiro/dashboard').then(r => r.json());
    // Renderiza cards e listas
}
```

---

## 15. financeiro_ordens.html
**Rota:** `/financeiro/ordens`

### Estrutura
```
topbar
└── content
    ├── filtros (status, colaborador, período)
    ├── tabela de O.S
    └── modal de detalhes
        ├── tabs: Detalhes | Prestações | Custos Empresa
        ├── botão "Aprovar O.S" (se status = emitida)
        ├── botão "Cancelar O.S"
        ├── botão "Reabrir O.S" (se status = encerrada/cancelada)
        ├── botão "Encerrar O.S" (se status = prestacao_aprovada)
        │
        ├── tab-prestacoes
        │   └── para cada item: botão Aprovar | Devolver (com campo de motivo)
        │
        └── tab-custos
            ├── lista de custos existentes (com botão remover)
            └── form "Adicionar custo"
                ├── select Tipo (hotel, passagem, alimentação, etc.)
                ├── input Descrição
                └── input Valor
```

### JavaScript principal
```javascript
async function aprovarOS(id)      { POST /api/os/ordens/{id}/aprovar }
async function cancelarOS(id)     { POST /api/os/ordens/{id}/cancelar }
async function reabrirOS(id)      { POST /api/os/ordens/{id}/reabrir }
async function encerrarOS(id)     { POST /api/os/ordens/{id}/encerrar }
async function aprovarPrestacao(id){ POST /api/os/prestacao/{id}/aprovar }
async function devolverPrestacao(id){ POST /api/os/prestacao/{id}/devolver }
async function adicionarCusto()   { POST /api/os/ordens/{id}/custos-empresa }
async function removerCusto(id)   { DELETE /api/os/custos-empresa/{id} }
```

---

## 16. financeiro_nova_os.html
**Rota:** `/financeiro/nova-os`

### Estrutura
Igual ao `os_nova.html` mas:
- O.S é criada com status `aprovada` (sem etapa `emitida`)
- Não precisa aguardar aprovação do financeiro

---

## 17. financeiro_prestacoes.html
**Rota:** `/financeiro/prestacoes`

### Estrutura
```
topbar
└── content
    ├── filtros (status: pendente, aprovado, devolvido, prestacao_aprovada, encerrada)
    ├── tabela de prestações
    │   └── colunas: O.S, Colaborador, Tipo, Valor, Status, Comprovantes, Ações
    └── modal de análise
        ├── detalhes do item
        ├── visualizador de comprovantes (imagens/PDFs inline)
        ├── botão "Aprovar"
        └── botão "Devolver" + campo de motivo
```

### Chips de status (todos os estados)
```html
<!-- Chips de filtro no toolbar -->
<button class="chip" onclick="setStatus('pendente', this)">⏳ Pendentes</button>
<button class="chip" onclick="setStatus('aprovado', this)">✅ Aprovadas</button>
<button class="chip" onclick="setStatus('devolvido', this)">↩ Devolvidas</button>
<button class="chip" onclick="setStatus('prestacao_aprovada', this)">✔ Prestação aprovada</button>
<button class="chip" onclick="setStatus('encerrada', this)">🔒 Encerradas</button>
<button class="chip active" onclick="setStatus('todos', this)">Todos</button>
```

---

## 18. financeiro_adiantamentos.html
**Rota:** `/financeiro/adiantamentos`

### Estrutura
```
topbar
└── content
    ├── tabela de adiantamentos (colaborador, valor, descrição, data)
    ├── botão "+ Novo Adiantamento"
    └── modal
        ├── select Colaborador
        ├── input Valor
        ├── input Descrição
        └── date Data
```

---

## 19. financeiro_contas.html
**Rota:** `/financeiro/contas`

### Estrutura
```
topbar
└── content
    ├── filtros (tipo: pagar/receber | status: pendente/pago | período)
    ├── resumo (total a pagar, total a receber, saldo)
    ├── tabela de contas
    │   ├── alerta visual para contas vencidas (linha vermelha)
    │   └── alerta para vencendo em 7 dias (linha amarela)
    ├── botão "+ Nova Conta"
    └── modal
        ├── select Tipo (pagar/receber)
        ├── input Descrição
        ├── input Valor
        ├── date Vencimento
        └── botão "Registrar pagamento" (se pendente)
```

### JavaScript
```javascript
async function carregar()        { GET /api/financeiro/contas }
async function salvarConta()     { POST /api/financeiro/contas }
async function deletarConta(id)  { DELETE /api/financeiro/contas/{id} }
async function pagarConta(id)    { POST /api/financeiro/contas/{id}/pagar }
```

---

## 20. financeiro_relatorios.html
**Rota:** `/financeiro/relatorios`

### Estrutura
```
topbar
└── content
    ├── cards de seleção de relatório (5 tipos)
    │   ├── 📊 Relatório Geral de O.S
    │   ├── 👤 Por Colaborador
    │   ├── 🏙️ Por Município
    │   ├── 💰 Contas a Pagar/Receber
    │   └── 💵 Adiantamentos
    ├── filtros (período, colaborador, município — aparecem conforme tipo)
    └── botão "Gerar PDF"
```

### JavaScript
```javascript
async function gerarRelatorio() {
    const body = {
        tipo: tipoSelecionado,
        data_inicio: ...,
        data_fim: ...,
        colaborador: ...,
    };
    // Abre PDF em nova aba
    const res = await fetch('/api/financeiro/relatorio-pdf', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
    });
    const blob = await res.blob();
    window.open(URL.createObjectURL(blob));
}
```

---

## 21. colaborador_os.html
**Rota:** `/colaborador/os`

### Estrutura (mobile-first)
```
<!-- SEM topbar tradicional -->
└── app (height: 100dvh)
    ├── main-content (área scrollável)
    │   ├── tela-dashboard
    │   │   ├── header com nome do colaborador
    │   │   ├── cards de stats
    │   │   │   ├── 🗓️ O.S no ano
    │   │   │   ├── 📅 Dias viajados
    │   │   │   ├── 💰 Valor em diárias
    │   │   │   └── 🚗 KM percorridos
    │   │   ├── cards de status
    │   │   │   ├── O.S abertas/em andamento
    │   │   │   └── O.S encerradas no ano
    │   │   └── ranking Top 5 Municípios
    │   │
    │   ├── tela-viagens
    │   │   ├── filtro de status (chips)
    │   │   └── lista de O.S (cards mobile)
    │   │       └── ao clicar → abre modal de detalhes
    │   │
    │   ├── tela-prestacoes
    │   │   ├── lista de prestações enviadas
    │   │   └── botão "+ Enviar prestação" → modal
    │   │
    │   └── tela-perfil
    │       ├── nome, cargo, departamento
    │       └── botão "Sair"
    │
    └── bottom-nav (fixo na base)
        ├── 🏠 Dashboard
        ├── 🚗 Viagens
        ├── 📋 Prestações
        └── 👤 Perfil
```

### JavaScript principal
```javascript
let meEmail = null;
let minhasOS = [];
let tabAtual = 'dashboard';

async function init() {
    meEmail = await fetch('/api/meu-email').then(r => r.json());
    await carregarDashboard();
}

async function carregarDashboard() {
    // GET /api/os/ordens?meu=1 — filtra por e-mail do colaborador
    // Calcula stats: dias, km, diárias, ranking municípios
}

async function mudarTab(tab) {
    tabAtual = tab;
    // Mostra/esconde telas
    // Carrega dados da aba se necessário
}

async function enviarPrestacao() {
    // FormData com: os_id, tipo, descricao, valor, arquivos[]
    const form = new FormData();
    form.append('os_id', osId);
    // Lê arquivos diretamente do input (sem variável global)
    const arquivos = document.getElementById('input-comprovantes').files;
    Array.from(arquivos).forEach(a => form.append('arquivos', a));
    await fetch('/api/os/ordens/{id}/prestacao', { method: 'POST', body: form });
}
```

### CSS mobile-first
```css
.app {
    height: 100dvh;          /* Altura dinâmica (considera barra mobile) */
    display: flex;
    flex-direction: column;
    max-width: 480px;         /* Limita em telas grandes */
    margin: 0 auto;
}
.main-content {
    flex: 1;
    overflow-y: auto;
    padding-bottom: 80px;     /* Espaço para bottom-nav */
}
.bottom-nav {
    position: fixed;
    bottom: 0;
    left: 0; right: 0;
    height: 64px;
    display: flex;
    background: var(--surface);
    border-top: 1px solid var(--border);
}
.nav-btn {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 2px;
    font-size: 10px;
    border: none;
    background: none;
    cursor: pointer;
}
.nav-btn.active { color: var(--accent); }
```

---

## PADRÕES DE MODAL (reutilizados em vários templates)

```html
<div class="modal-overlay" id="modal">
    <div class="modal">
        <div class="modal-header">
            <div class="modal-title">Título</div>
            <button class="modal-close" onclick="fecharModal()">×</button>
        </div>
        <div class="modal-tabs">
            <button class="tab active" onclick="mudarTab('aba1', this)">Aba 1</button>
            <button class="tab" onclick="mudarTab('aba2', this)">Aba 2</button>
        </div>
        <div class="modal-body" id="tab-aba1">
            <!-- conteúdo -->
        </div>
        <div class="modal-body" id="tab-aba2" style="display:none">
            <!-- conteúdo -->
        </div>
        <div class="modal-footer">
            <button class="btn-secondary" onclick="fecharModal()">Fechar</button>
            <button class="btn-primary" onclick="confirmar()">Confirmar</button>
        </div>
    </div>
</div>
```

```javascript
// Abrir/fechar modal
function abrirModal()  { document.getElementById('modal').classList.add('open'); }
function fecharModal() { document.getElementById('modal').classList.remove('open'); }

// Fechar ao clicar fora
document.getElementById('modal').addEventListener('click', function(e) {
    if (e.target === this) fecharModal();
});
```

---

## PADRÕES DE BADGE/STATUS

```javascript
// Badges de status de chamados
function badgeStatus(status) {
    const map = {
        aberto:                 { cls: 'aberto',    label: '📤 Enviado' },
        em_analise:             { cls: 'em_analise',label: '🔍 Em análise' },
        aguardando_colaborador: { cls: 'aguardando',label: '⚠️ Sua resposta' },
        pendente_dev:           { cls: 'pend',      label: '✅ Resposta recebida' },
        fechado:                { cls: 'fechado',   label: '✔ Resolvido' },
    };
    const b = map[status] || { cls: '', label: status };
    return `<span class="badge ${b.cls}">${b.label}</span>`;
}

// Badges de status de O.S
function badgeStatusOS(status) {
    const map = {
        emitida:             '📋 Emitida',
        aprovada:            '✅ Aprovada',
        prestacao_enviada:   '📤 Prestação enviada',
        prestacao_devolvida: '↩ Devolvida',
        prestacao_aprovada:  '✔ Prestação aprovada',
        encerrada:           '🔒 Encerrada',
        cancelada:           '❌ Cancelada',
    };
    return `<span class="badge status-${status}">${map[status] || status}</span>`;
}

// Badges de prioridade
function badgePrioridade(p) {
    const map = {
        urgente: '🚨 Urgente',
        alta:    '🔴 Alta',
        media:   '🟡 Média',
        baixa:   '🟢 Baixa',
    };
    return `<span class="pri-badge ${p}">${map[p] || p}</span>`;
}
```

---

## RENDERIZAÇÃO DE ANEXOS

```javascript
// Função padrão para renderizar anexo por URL
function renderAnexo(url, index) {
    if (!url) return '';
    const isImg = /\.(jpg|jpeg|png|gif|webp)/i.test(url);
    const isVid = /\.(mp4|mov|avi|webm)/i.test(url);
    const label = index !== undefined
        ? `<div style="font-size:11px;color:var(--text3);margin-bottom:4px">📎 Anexo ${index + 1}</div>`
        : '';
    if (isImg) return label + `<div class="msg-anexo"><img src="${url}" onclick="window.open(this.src)" /></div>`;
    if (isVid) return label + `<div class="msg-anexo"><video src="${url}" controls></video></div>`;
    return label + `<div class="msg-anexo"><a href="${url}" target="_blank">📄 Ver arquivo</a></div>`;
}

// Renderizar múltiplos anexos de uma mensagem
function renderAnexosMensagem(m) {
    const urls = m.evidencia_urls || (m.evidencia_url ? [m.evidencia_url] : []);
    return urls.map((u, i) => renderAnexo(u, urls.length > 1 ? i : undefined)).join('');
}
```

---

## DICAS PARA O PROGRAMADOR

### Onde adicionar nova funcionalidade no modal de chamado
1. `dashboard.html` → aba "Admin" → função `enviarMensagem()` ou crie novo botão
2. `meus_chamados.html` → mesma estrutura mas sem aba Admin

### Onde fica o cálculo de diárias
- `os_nova.html` → função `calcular()`
- Fórmula: `dias × diária + (meia_diaria ? meia : 0) + adiantamentos`

### Onde fica o filtro por e-mail do colaborador
- `colaborador_os.html` → `fetch('/api/os/ordens?meu=1')`
- `main.py` → rota `GET /api/os/ordens` → `if request.query_params.get('meu'): filtrar por email`

### Onde fica a lógica de redirecionamento do portal
- `portal.html` → função `carregarPortal()` → verifica array `modulos` do perfil

### Como adicionar novo módulo
1. Criar template HTML em `templates/`
2. Adicionar rota GET na página em `main.py`
3. Adicionar APIs necessárias em `main.py`
4. Adicionar valor no campo `modulos` da tabela `perfis`
5. Adicionar card no `portal.html`
6. Adicionar checkbox no modal de perfil em `configuracoes_gerais.html`

---

*Guia gerado em Abril/2026 — Inovatus Sistemas*
