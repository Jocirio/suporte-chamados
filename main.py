from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, FileResponse
from supabase import create_client
from datetime import datetime, timedelta, timezone
import os
import resend
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

# --- ADICIONE ESTA ROTA ABAIXO ---

@app.get("/api/os/ordens/{id}")
async def api_os_ordem(id: str, request: Request):
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=401)
    try:
        # Busca os dados da O.S, Cliente e Departamento
        resultado = supabase.table("os_ordens").select(
            "*, os_departamentos(nome,valor_diaria,valor_meia_diaria), clientes(nome,estado,distancia_km)"
        ).eq("id", id).execute()
        
        if not resultado.data:
            raise HTTPException(status_code=404, detail="Ordem não encontrada")
            
        os_data = resultado.data[0]
        
        # Busca o telefone do colaborador para o WhatsApp
        email_colab = os_data.get("colaborador_email")
        perfil = supabase.table("perfis").select("telefone").eq("email", email_colab).execute()
        
        # Monta a estrutura que o frontend espera
        os_data["perfis"] = {"telefone": perfil.data[0].get("telefone") if perfil.data else ""}
        
        return os_data
    except Exception as e:
        print(f"Erro na API de detalhes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --------------------------------

SUPABASE_URL = os.getenv("SUPABASE_URL") or "https://wvjsbgfnhdapqtinewgb.supabase.co"
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Ind2anNiZ2ZuaGRhcHF0aW5ld2diIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzYzNjIzMTAsImV4cCI6MjA5MTkzODMxMH0.MXpfYhlL0tbr-d7RRC2XZL7a7eFgblqzAHajbJq2zQ8"
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Ind2anNiZ2ZuaGRhcHF0aW5ld2diIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NjM2MjMxMCwiZXhwIjoyMDkxOTM4MzEwfQ.eKy5JHGypyKWFDFxP2xLe93jhvQNVSWbAxjk37yaJRM"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
supabase_admin = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
resend.api_key = os.getenv("RESEND_KEY") or "re_KXpHjVbT_N7URPgNpgmMxomTotVpfnrD9"

def registrar_historico(chamado_id: str, evento: str, descricao: str, autor: str):
    try:
        supabase.table("chamados_historico").insert({
            "chamado_id": chamado_id,
            "evento": evento,
            "descricao": descricao,
            "autor": autor
        }).execute()
    except Exception as e:
        print(f"Erro ao registrar histórico: {e}")

async def fazer_upload(arquivo: UploadFile) -> str:
    if not arquivo or not arquivo.filename:
        return ""
    conteudo = await arquivo.read()
    nome = f"{os.urandom(8).hex()}_{arquivo.filename}"
    pasta = "/root/suporte-chamados/static/uploads"
    os.makedirs(pasta, exist_ok=True)
    with open(f"{pasta}/{nome}", "wb") as f:
        f.write(conteudo)
    return f"https://voosuporte.com.br/static/uploads/{nome}"

def notificar_admins(assunto: str, html: str):
    try:
        admins = supabase.table("perfis").select("email").eq("role", "admin").eq("ativo", True).execute()
        for admin in admins.data:
            try:
                resend.Emails.send({
                    "from": "Voo Suporte <noreply@voosuporte.com.br>",
                    "to": admin["email"],
                    "subject": assunto,
                    "html": html
                })
            except Exception as e:
                print(f"Erro e-mail admin {admin['email']}: {e}")
    except Exception as e:
        print(f"Erro ao buscar admins: {e}")

def enviar_email_os_colaborador(os_criada: dict, body: dict):
    try:
        resend.Emails.send({
            "from": "Voo Suporte <noreply@voosuporte.com.br>",
            "to": body["colaborador_email"],
            "subject": f"📋 Nova Ordem de Serviço emitida — {os_criada['numero']}",
            "html": f"""<div style="font-family:sans-serif;max-width:600px;margin:0 auto;padding:24px">
              <h2 style="color:#059669">Ordem de Serviço emitida</h2>
              <p>Olá, <strong>{body['colaborador_nome']}</strong>!</p>
              <p>Uma nova O.S foi emitida para você.</p>
              <table style="width:100%;border-collapse:collapse;margin:20px 0">
                <tr><td style="padding:8px;color:#888;font-size:12px;width:120px">Número</td><td style="padding:8px;font-size:13px;font-weight:600;color:#059669">{os_criada['numero']}</td></tr>
                <tr style="background:#f9fafb"><td style="padding:8px;color:#888;font-size:12px">Cargo</td><td style="padding:8px;font-size:13px">{body['cargo']}</td></tr>
                <tr><td style="padding:8px;color:#888;font-size:12px">Data de ida</td><td style="padding:8px;font-size:13px">{body['data_ida']}</td></tr>
                <tr style="background:#f9fafb"><td style="padding:8px;color:#888;font-size:12px">Data de volta</td><td style="padding:8px;font-size:13px">{body['data_volta']}</td></tr>
                <tr><td style="padding:8px;color:#888;font-size:12px">Transporte</td><td style="padding:8px;font-size:13px">{body['meio_transporte']}</td></tr>
                <tr style="background:#f9fafb"><td style="padding:8px;color:#888;font-size:12px">Total de dias</td><td style="padding:8px;font-size:13px">{body['total_dias']} dia(s)</td></tr>
                <tr><td style="padding:8px;color:#888;font-size:12px">Valor total</td><td style="padding:8px;font-size:13px;font-weight:600;color:#059669">R$ {float(body['valor_total']):.2f}</td></tr>
              </table>
              <div style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:8px;padding:14px;margin-bottom:16px">
                <p style="font-size:12px;color:#888;margin-bottom:4px">Serviços a executar:</p>
                <p style="font-size:13px;color:#111;line-height:1.6;margin:0">{body['servicos']}</p>
              </div>
              <p style="color:#888;font-size:12px">Acesse o portal para visualizar todos os detalhes da sua O.S.</p>
              <a href="https://voosuporte.com.br/colaborador/os" style="display:inline-block;background:#059669;color:#fff;padding:10px 20px;border-radius:8px;text-decoration:none;font-size:13px;font-weight:600;margin-top:8px">Ver minhas O.S →</a>
            </div>"""
        })
    except Exception as e:
        print(f"Erro e-mail O.S colaborador: {e}")

# --- ROTAS PWA CORRIGIDAS ---
@app.get("/manifest.json")
async def serve_manifest():
    return FileResponse("static/manifest.json", media_type="application/manifest+json")

@app.get("/service-worker.js")
async def serve_sw():
    return FileResponse("static/service-worker.js", media_type="application/javascript")
# ----------------------------

@app.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="login.html")

@app.get("/portal", response_class=HTMLResponse)
async def portal(request: Request):
    token = request.cookies.get("token")
    if not token:
        return RedirectResponse(url="/")
    return templates.TemplateResponse(request=request, name="portal.html")

@app.get("/configuracoes", response_class=HTMLResponse)
async def tela_configuracoes(request: Request):
    token = request.cookies.get("token")
    role = request.cookies.get("role")
    if not token or role != "admin":
        return RedirectResponse(url="/")
    return templates.TemplateResponse(request=request, name="configuracoes_gerais.html")

@app.get("/novo-chamado", response_class=HTMLResponse)
async def novo_chamado(request: Request):
    token = request.cookies.get("token")
    if not token:
        return RedirectResponse(url="/")
    return templates.TemplateResponse(request=request, name="formulario.html")

def tem_modulo(request: Request, modulo: str) -> bool:
    modulos = request.cookies.get("modulos", "")
    return modulo in modulos.split(",")

@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    token = request.cookies.get("token")
    role = request.cookies.get("role")
    # Permite admin do sistema OU usuário com módulo chamados_gestor
    if not token or (role != "admin" and not tem_modulo(request, "chamados_gestor")):
        return RedirectResponse(url="/portal")
    return templates.TemplateResponse(request=request, name="dashboard.html")

@app.get("/admin/clientes", response_class=HTMLResponse)
async def admin_clientes(request: Request):
    token = request.cookies.get("token")
    role = request.cookies.get("role")
    if not token or role != "admin":
        return RedirectResponse(url="/")
    return templates.TemplateResponse(request=request, name="clientes.html")

@app.get("/admin/usuarios", response_class=HTMLResponse)
async def admin_usuarios(request: Request):
    token = request.cookies.get("token")
    role = request.cookies.get("role")
    if not token or role != "admin":
        return RedirectResponse(url="/")
    return templates.TemplateResponse(request=request, name="usuarios.html")

@app.get("/relatorios", response_class=HTMLResponse)
async def relatorios(request: Request):
    token = request.cookies.get("token")
    role = request.cookies.get("role")
    if not token or (role != "admin" and not tem_modulo(request, "chamados_gestor")):
        return RedirectResponse(url="/portal")
    return templates.TemplateResponse(request=request, name="relatorios.html")

@app.get("/meus-chamados", response_class=HTMLResponse)
async def meus_chamados(request: Request):
    token = request.cookies.get("token")
    if not token:
        return RedirectResponse(url="/")
    return templates.TemplateResponse(request=request, name="meus_chamados.html")

@app.get("/os", response_class=HTMLResponse)
async def os_dashboard(request: Request):
    token = request.cookies.get("token")
    if not token:
        return RedirectResponse(url="/")
    return templates.TemplateResponse(request=request, name="os_dashboard.html")

@app.get("/os/nova", response_class=HTMLResponse)
async def os_nova(request: Request):
    token = request.cookies.get("token")
    if not token:
        return RedirectResponse(url="/")
    return templates.TemplateResponse(request=request, name="os_nova.html")

@app.get("/colaborador/os", response_class=HTMLResponse)
async def colaborador_os(request: Request):
    token = request.cookies.get("token")
    if not token:
        return RedirectResponse(url="/")
    return templates.TemplateResponse(request=request, name="colaborador_os.html")

@app.get("/os/config", response_class=HTMLResponse)
async def os_config(request: Request):
    token = request.cookies.get("token")
    if not token:
        return RedirectResponse(url="/")
    return templates.TemplateResponse(request=request, name="os_config.html")

@app.get("/os/financeiro", response_class=HTMLResponse)
async def os_financeiro(request: Request):
    token = request.cookies.get("token")
    if not token:
        return RedirectResponse(url="/")
    return templates.TemplateResponse(request=request, name="os_financeiro.html")

@app.get("/api/financeiro/dashboard")
async def api_financeiro_dashboard(request: Request):
    token = request.cookies.get("token")
    if not token: 
        raise HTTPException(status_code=401)
    try:
        # 1. Contagem de O.S. Pendentes
        pendentes = supabase.table("os_ordens").select("id", count="exact").eq("status", "pendente").execute().count
        
        # 2. Contas Vencidas
        hoje = datetime.now().date().isoformat()
        vencidas = supabase.table("financeiro_contas").select("id", count="exact").lt("vencimento", hoje).neq("status", "pago").execute().count

        # 3. Resumo de Saldos
        saldos = supabase.table("resumo_financeiro_colaboradores").select("*").execute().data

        return {
            "os_aguardando_aprovacao": pendentes or 0,
            "contas_vencidas": vencidas or 0,
            "prestacoes_pendentes": 0,
            "saldo_colaboradores": saldos or []
        }
    except Exception as e:
        print(f"Erro dashboard financeiro: {e}")
        return {
            "os_aguardando_aprovacao": 0, 
            "contas_vencidas": 0, 
            "prestacoes_pendentes": 0, 
            "saldo_colaboradores": []
        }

@app.get("/os/ordens/{id}/pdf")
async def gerar_pdf_os(id: str, request: Request):
    token = request.cookies.get("token")
    role = request.cookies.get("role")
    if not token:
        return RedirectResponse(url="/")
    try:
        from weasyprint import HTML
        
        user = supabase.auth.get_user(token)
        perfil = supabase.table("perfis").select("modulos").eq("id", str(user.user.id)).execute()
        modulos = perfil.data[0].get("modulos") or [] if perfil.data else []
        is_financeiro = role == "admin" or "financeiro" in modulos or "ordens_servico" in modulos

        os_res = supabase.table("os_ordens").select("*,os_departamentos(nome,valor_diaria,valor_meia_diaria),clientes(nome,estado,distancia_km)").eq("id", id).execute()
        if not os_res.data:
            raise HTTPException(status_code=404)
        o = os_res.data[0]

        custos_emp = supabase.table("os_custos_empresa").select("*").eq("os_id", id).execute()
        # Busca adiantamentos diretamente (este endpoint não usa o enriquecimento do list)
        try:
            adiant_res = supabase.table("os_adiantamentos").select("*").eq("os_id", id).execute()
            adiantamentos = adiant_res.data or []
        except Exception:
            adiantamentos = []

        def fmt(v): return f"R$ {float(v or 0):.2f}".replace(".", ",")
        def fmtd(d): return d[8:10]+"/"+d[5:7]+"/"+d[0:4] if d and len(d) >= 10 else "—"

        total_diarias = float(o.get("valor_total_diarias") or 0)
        total_adiant = sum(float(a.get("valor", 0)) for a in adiantamentos)
        total_colab = float(o.get("valor_total") or 0)
        total_empresa = sum(float(c.get("valor", 0)) for c in custos_emp.data)
        saldo_colab = total_colab - total_adiant  # positivo = empresa deve ao colaborador
        investimento_total = total_colab + total_empresa

        depto = (o.get("os_departamentos") or {})
        mun = (o.get("clientes") or {})

        adiant_rows = "".join(
            f"<tr><td style='padding:7px 10px;border-bottom:1px solid #f1f5f9'>Adiantamento — {a.get('descricao','')}</td><td style='padding:7px 10px;border-bottom:1px solid #f1f5f9;text-align:right;color:#6366f1;font-weight:600'>{fmt(a.get('valor',0))}</td></tr>"
            for a in adiantamentos
        )
        custos_rows = ""
        if is_financeiro:
            custos_rows = "".join(
                f"<tr><td style='padding:7px 10px;border-bottom:1px solid #f1f5f9;color:#dc2626'>Custo Empresa — {c.get('descricao','')}</td><td style='padding:7px 10px;border-bottom:1px solid #f1f5f9;text-align:right;color:#dc2626;font-weight:600'>{fmt(c.get('valor',0))}</td></tr>"
                for c in custos_emp.data
            )

        saldo_label = "A receber do colaborador" if saldo_colab < 0 else ("Empresa deve ao colaborador" if saldo_colab > 0 else "Quites")
        saldo_cor = "#059669" if saldo_colab <= 0 else "#dc2626"

        html_content = f"""<!DOCTYPE html>
<html lang="pt-br"><head><meta charset="UTF-8">
<style>
  @page {{ size: A4; margin: 1.5cm; }}
  body {{ font-family: 'Helvetica Neue', Arial, sans-serif; color: #1e293b; font-size: 11px; line-height: 1.5; }}
  .header {{ display: flex; justify-content: space-between; align-items: flex-start; padding-bottom: 14px; border-bottom: 2px solid #d97706; margin-bottom: 20px; }}
  .brand {{ font-size: 18px; font-weight: 700; color: #d97706; }}
  .brand-sub {{ font-size: 11px; color: #94a3b8; margin-top: 2px; }}
  .os-num {{ font-size: 24px; font-weight: 700; color: #1e293b; font-family: monospace; }}
  .os-num-label {{ font-size: 10px; color: #94a3b8; text-transform: uppercase; letter-spacing: .06em; text-align: right; }}
  .info-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 20px; background: #f8fafc; border-radius: 8px; padding: 14px; border: 1px solid #e2e8f0; }}
  .info-item label {{ font-size: 9px; color: #94a3b8; text-transform: uppercase; letter-spacing: .06em; display: block; margin-bottom: 3px; }}
  .info-item span {{ font-size: 12px; font-weight: 600; color: #1e293b; }}
  .section-title {{ font-size: 10px; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: .07em; margin-bottom: 8px; padding-bottom: 4px; border-bottom: 1px solid #e2e8f0; }}
  table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; }}
  th {{ background: #f8fafc; padding: 8px 10px; text-align: left; font-size: 9px; color: #64748b; text-transform: uppercase; border: 1px solid #e2e8f0; }}
  td {{ padding: 7px 10px; border-bottom: 1px solid #f1f5f9; font-size: 11px; }}
  .total-row {{ background: #fef3c7; font-weight: 700; }}
  .total-row td {{ padding: 10px; border: 1px solid #fcd34d; }}
  .saldo-box {{ border-radius: 8px; padding: 12px 16px; margin-bottom: 16px; display: flex; justify-content: space-between; align-items: center; }}
  .footer {{ text-align: center; font-size: 9px; color: #94a3b8; margin-top: 24px; padding-top: 12px; border-top: 1px solid #e2e8f0; }}
  -webkit-print-color-adjust: exact; print-color-adjust: exact;
</style>
</head><body>
  <div class="header">
    <div><div class="brand">Voo Suporte</div><div class="brand-sub">Ordem de Serviço</div></div>
    <div><div class="os-num-label">Número da O.S</div><div class="os-num">{o.get('numero','—')}</div></div>
  </div>

  <div class="info-grid">
    <div class="info-item"><label>Colaborador</label><span>{o.get('colaborador_nome', o.get('colaborador_email','—'))}</span></div>
    <div class="info-item"><label>Município de destino</label><span>{mun.get('nome','—')}{(' — '+mun['estado']) if mun.get('estado') else ''}</span></div>
    <div class="info-item"><label>Departamento</label><span>{depto.get('nome','—')}</span></div>
    <div class="info-item"><label>Status</label><span>{o.get('status','—').replace('_',' ').title()}</span></div>
    <div class="info-item"><label>Data de ida</label><span>{fmtd(o.get('data_ida'))}</span></div>
    <div class="info-item"><label>Data de volta</label><span>{fmtd(o.get('data_volta'))}</span></div>
    <div class="info-item"><label>Tipo de transporte</label><span>{o.get('tipo_transporte','—')}</span></div>
    <div class="info-item"><label>Total de dias</label><span>{o.get('total_dias','—')} dia(s)</span></div>
  </div>

  {"<div class='section-title'>Serviços previstos</div><p style='font-size:11px;color:#475569;background:#f8fafc;border-radius:6px;padding:10px;border:1px solid #e2e8f0;margin-bottom:20px'>" + (o.get('servicos_previstos') or '—') + "</p>" if o.get('servicos_previstos') else ""}

  <div class="section-title">Composição financeira — Colaborador</div>
  <table>
    <thead><tr><th>Descrição</th><th style="text-align:right">Valor</th></tr></thead>
    <tbody>
      <tr><td>Diárias ({o.get('total_dias','—')} × {fmt(float(o.get('valor_diaria_base') or (total_diarias/max(int(o.get('total_dias') or 1),1))))})</td><td style="text-align:right;font-weight:600;color:#d97706">{fmt(total_diarias)}</td></tr>
      {adiant_rows if adiant_rows else "<tr><td style='color:#94a3b8;font-style:italic'>Sem adiantamentos</td><td></td></tr>"}
      <tr class="total-row"><td>Total a receber pelo colaborador</td><td style="text-align:right;color:#d97706">{fmt(total_colab)}</td></tr>
    </tbody>
  </table>

  {f'''<div class="section-title">Custos da empresa</div>
  <table>
    <thead><tr><th>Tipo</th><th>Descrição</th><th style="text-align:right">Valor</th></tr></thead>
    <tbody>{custos_rows if custos_rows else "<tr><td colspan='3' style='color:#94a3b8;font-style:italic;padding:10px'>Nenhum custo de empresa registrado.</td></tr>"}</tbody>
  </table>''' if is_financeiro else ""}

  <div class="saldo-box" style="background:{'#f0fdf4' if saldo_colab >= 0 else '#fef2f2'};border:1px solid {'#86efac' if saldo_colab >= 0 else '#fecaca'}">
    <div style="font-size:12px;color:#475569">{saldo_label}</div>
    <div style="font-size:18px;font-weight:700;color:{saldo_cor};font-family:monospace">{fmt(abs(saldo_colab))}</div>
  </div>

  {f'<div style="background:#1e293b;color:white;border-radius:8px;padding:14px 18px;display:flex;justify-content:space-between;align-items:center;margin-bottom:16px"><span style="font-size:12px">Investimento total (collab + empresa)</span><span style="font-size:18px;font-weight:700;font-family:monospace">{fmt(investimento_total)}</span></div>' if is_financeiro else ""}

  <div class="footer">
    Voo Suporte · O.S {o.get('numero','—')} · Gerado em {datetime.now().strftime('%d/%m/%Y às %H:%M')} · {o.get('colaborador_email','')}
  </div>
</body></html>"""

        pdf_bytes = HTML(string=html_content).write_pdf()
        return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f"inline; filename=OS_{o['numero']}.pdf"})
    except Exception as e:
        print(f"Erro no PDF: {e}")
        raise HTTPException(status_code=500, detail="Erro ao gerar PDF")
        
@app.get("/financeiro", response_class=HTMLResponse)
async def financeiro_hub(request: Request):
    token = request.cookies.get("token")
    if not token:
        return RedirectResponse(url="/")
    return templates.TemplateResponse(request=request, name="financeiro_dashboard.html")

@app.get("/financeiro/ordens", response_class=HTMLResponse)
async def financeiro_ordens(request: Request):
    token = request.cookies.get("token")
    if not token:
        return RedirectResponse(url="/")
    return templates.TemplateResponse(request=request, name="financeiro_ordens.html")

@app.get("/financeiro/nova-os", response_class=HTMLResponse)
async def financeiro_nova_os(request: Request):
    token = request.cookies.get("token")
    if not token:
        return RedirectResponse(url="/")
    return templates.TemplateResponse(request=request, name="financeiro_nova_os.html")

@app.get("/financeiro/prestacoes", response_class=HTMLResponse)
async def financeiro_prestacoes(request: Request):
    token = request.cookies.get("token")
    if not token:
        return RedirectResponse(url="/")
    return templates.TemplateResponse(request=request, name="financeiro_prestacoes.html")

@app.get("/financeiro/adiantamentos", response_class=HTMLResponse)
async def financeiro_adiantamentos(request: Request):
    token = request.cookies.get("token")
    if not token:
        return RedirectResponse(url="/")
    return templates.TemplateResponse(request=request, name="financeiro_adiantamentos.html")

@app.get("/financeiro/contas", response_class=HTMLResponse)
async def financeiro_contas(request: Request):
    token = request.cookies.get("token")
    if not token:
        return RedirectResponse(url="/")
    return templates.TemplateResponse(request=request, name="financeiro_contas.html")

@app.get("/financeiro/relatorios", response_class=HTMLResponse)
async def financeiro_relatorios(request: Request):
    token = request.cookies.get("token")
    if not token:
        return RedirectResponse(url="/")
    return templates.TemplateResponse(request=request, name="financeiro_relatorios.html")

# Rota para a página de Auditoria (o print que você mandou)
@app.get("/financeiro/auditoria", response_class=HTMLResponse)
async def pagina_auditoria_financeira(request: Request):
    token = request.cookies.get("token")
    if not token: return RedirectResponse(url="/")
    return templates.TemplateResponse(request=request, name="financeiro_dashboard.html")

# Rota para a página de Contas (Pagar/Receber)
@app.get("/financeiro/contas-geral", response_class=HTMLResponse)
async def pagina_contas_financeiro(request: Request):
    token = request.cookies.get("token")
    if not token: return RedirectResponse(url="/")
    return templates.TemplateResponse(request=request, name="financeiro_contas.html")

# ===================== AUTH =====================

@app.post("/login")
async def login(email: str = Form(...), senha: str = Form(...)):
    try:
        res = supabase.auth.sign_in_with_password({"email": email, "password": senha})
        perfil = supabase.table("perfis").select("role,modulos").eq("id", str(res.user.id)).execute()
        role = perfil.data[0]["role"] if perfil.data else "colaborador"
        modulos = perfil.data[0].get("modulos") or [] if perfil.data else []
        # Admin sempre tem configuracoes; demais módulos são configurados individualmente
        if role == "admin":
            if "configuracoes" not in modulos:
                modulos = modulos + ["configuracoes"]
        response = RedirectResponse(url="/portal", status_code=302)
        response.set_cookie("token", res.session.access_token, httponly=True)
        response.set_cookie("role", role, httponly=True)
        response.set_cookie("modulos", ",".join(modulos), httponly=True)
        return response
    except Exception as e:
        return RedirectResponse(url="/?erro=1", status_code=302)
@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie("token")
    response.delete_cookie("role")
    return response

@app.post("/api/financeiro/relatorio-pdf")
async def relatorio_pdf(request: Request):
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=401)
    try:
        from weasyprint import HTML
        body = await request.json()
        tipo = body.get("tipo")
        dados = body.get("dados", {})

        def fmt(v): return f"R$ {float(v or 0):.2f}".replace(".", ",")
        def fmtdata(d):
            if not d: return "—"
            return d[8:10] + "/" + d[5:7] + "/" + d[0:4]

        titulo = dados.get("titulo", "Relatório")
        inicio = dados.get("inicio", "")
        fim = dados.get("fim", "")
        periodo_str = f"{fmtdata(inicio)} até {fmtdata(fim)}" if inicio or fim else "Todos os períodos"

        tbody = ""
        thead = ""

        if tipo == "periodo":
            lista = dados.get("lista", [])
            thead = "<tr><th>Nº</th><th>Colaborador</th><th>Município</th><th>Período</th><th>Status</th><th>Colaborador</th><th>Empresa</th><th>Total</th></tr>"
            total = sum(float(o.get("valor_total") or 0) for o in lista)
            total_emp = sum(float(o.get("valor_total_empresa") or 0) for o in lista)
            for o in lista:
                tot = float(o.get("valor_total") or 0) + float(o.get("valor_total_empresa") or 0)
                mun = (o.get("clientes") or {}).get("nome", "—")
                tbody += f"<tr><td>{o['numero']}</td><td>{o['colaborador_nome']}</td><td>{mun}</td><td>{fmtdata(o['data_ida'])} → {fmtdata(o['data_volta'])}</td><td>{o['status']}</td><td>{fmt(o.get('valor_total'))}</td><td>{fmt(o.get('valor_total_empresa'))}</td><td><strong>{fmt(tot)}</strong></td></tr>"
            tbody += f"<tr style='background:#fef3c7;font-weight:bold'><td colspan='5'>TOTAL ({len(lista)} O.S)</td><td>{fmt(total)}</td><td>{fmt(total_emp)}</td><td>{fmt(total+total_emp)}</td></tr>"

        elif tipo == "colab":
            lista = dados.get("lista", [])
            thead = "<tr><th>Nº</th><th>Município</th><th>Período</th><th>Dias</th><th>Status</th><th>Diárias</th><th>Adiantamentos</th></tr>"
            total_d = sum(float(o.get("valor_total_diarias") or 0) for o in lista)
            total_a = sum(sum(float(a.get("valor", 0)) for a in (o.get("adiantamentos") or [])) for o in lista)
            for o in lista:
                adiant = sum(float(a.get("valor", 0)) for a in (o.get("adiantamentos") or []))
                mun = (o.get("clientes") or {}).get("nome", "—")
                tbody += f"<tr><td>{o['numero']}</td><td>{mun}</td><td>{fmtdata(o['data_ida'])} → {fmtdata(o['data_volta'])}</td><td>{o['total_dias']}</td><td>{o['status']}</td><td>{fmt(o.get('valor_total_diarias'))}</td><td>{fmt(adiant)}</td></tr>"
            tbody += f"<tr style='background:#fef3c7;font-weight:bold'><td colspan='5'>TOTAL</td><td>{fmt(total_d)}</td><td>{fmt(total_a)}</td></tr>"

        elif tipo == "cliente":
            por_cliente = dados.get("porCliente", {})
            thead = "<tr><th>Município</th><th>Qtd O.S</th><th>Custo Colaborador</th><th>Custo Empresa</th><th>Total</th></tr>"
            total_d = sum(v["diarias"] for v in por_cliente.values())
            total_e = sum(v["empresa"] for v in por_cliente.values())
            for nome, v in por_cliente.items():
                tbody += f"<tr><td>{nome}</td><td>{v['os']}</td><td>{fmt(v['diarias'])}</td><td>{fmt(v['empresa'])}</td><td><strong>{fmt(v['diarias']+v['empresa'])}</strong></td></tr>"
            tbody += f"<tr style='background:#fef3c7;font-weight:bold'><td>TOTAL</td><td>{sum(v['os'] for v in por_cliente.values())}</td><td>{fmt(total_d)}</td><td>{fmt(total_e)}</td><td>{fmt(total_d+total_e)}</td></tr>"

        elif tipo == "contas":
            lista = dados.get("lista", [])
            thead = "<tr><th>Tipo</th><th>Descrição</th><th>Cliente</th><th>Vencimento</th><th>Status</th><th>Valor</th></tr>"
            total_p = sum(float(c["valor"]) for c in lista if c["tipo"] == "pagar")
            total_r = sum(float(c["valor"]) for c in lista if c["tipo"] == "receber")
            for c in lista:
                cliente = (c.get("clientes") or {}).get("nome", "—")
                tbody += f"<tr><td>{c['tipo']}</td><td>{c['descricao']}</td><td>{cliente}</td><td>{fmtdata(c['vencimento'])}</td><td>{c['status']}</td><td>{fmt(c['valor'])}</td></tr>"
            tbody += f"<tr style='background:#fef3c7;font-weight:bold'><td colspan='5'>TOTAL PAGAR / RECEBER</td><td>{fmt(total_p)} / {fmt(total_r)}</td></tr>"

        elif tipo == "adiant":
            por_colab = dados.get("porColab", {})
            thead = "<tr><th>Colaborador</th><th>Adiant. em O.S</th><th>Adiant. Avulsos</th><th>Total</th></tr>"
            t_os = sum(v["os"] for v in por_colab.values())
            t_av = sum(v["avulso"] for v in por_colab.values())
            for email, v in por_colab.items():
                tbody += f"<tr><td>{v['nome']}<br><small style='color:#888'>{email}</small></td><td>{fmt(v['os'])}</td><td>{fmt(v['avulso'])}</td><td><strong>{fmt(v['os']+v['avulso'])}</strong></td></tr>"
            tbody += f"<tr style='background:#fef3c7;font-weight:bold'><td>TOTAL</td><td>{fmt(t_os)}</td><td>{fmt(t_av)}</td><td>{fmt(t_os+t_av)}</td></tr>"

        html_content = f"""<!DOCTYPE html>
        <html lang="pt-br"><head><meta charset="UTF-8">
        <style>
          @page {{ size: A4; margin: 1.5cm; }}
          body {{ font-family: sans-serif; font-size: 11px; color: #111; }}
          .header {{ border-bottom: 2px solid #d97706; padding-bottom: 10px; margin-bottom: 20px; display: flex; justify-content: space-between; }}
          h1 {{ font-size: 16px; color: #d97706; margin: 0; }}
          table {{ width: 100%; border-collapse: collapse; }}
          th {{ background: #fef3c7; color: #92400e; font-size: 10px; text-transform: uppercase; padding: 8px; text-align: left; border: 1px solid #fcd34d; }}
          td {{ padding: 7px 8px; border: 1px solid #e5e7eb; font-size: 11px; }}
          tr:nth-child(even) {{ background: #fafafa; }}
        </style></head><body>
          <div class="header">
            <div><h1>{titulo}</h1><p style="color:#888;font-size:10px;margin:4px 0 0">Período: {periodo_str}</p></div>
            <div style="text-align:right;font-size:10px;color:#888">Voo Suporte<br>Emitido em: {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M')}</div>
          </div>
          <table><thead>{thead}</thead><tbody>{tbody}</tbody></table>
        </body></html>"""

        from fastapi.responses import Response
        pdf_bytes = HTML(string=html_content).write_pdf()
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"inline; filename=relatorio_{tipo}.pdf"}
        )
    except Exception as e:
        print(f"Erro PDF relatório: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ===================== MÓDULO COLABORADOR =====================

@app.post("/api/os/ordens/{id}/prestacao/anexos")
async def adicionar_anexos_prestacao(id: str, prestacao_id: str = Form(...), request: Request = None, arquivos: list[UploadFile] = File(...)):
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=401)
    urls = []
    for arq in arquivos:
        if arq.filename:
            url = await fazer_upload(arq)
            if url:
                urls.append(url)
    if urls:
        prestacao = supabase.table("os_prestacao_contas").select("comprovante_urls").eq("id", prestacao_id).execute()
        if prestacao.data:
            existentes = prestacao.data[0].get("comprovante_urls") or []
            todas = existentes + urls
            supabase.table("os_prestacao_contas").update({"comprovante_urls": todas}).eq("id", prestacao_id).execute()
    return {"status": "enviado", "urls": urls}
    
@app.get("/registrar", response_class=HTMLResponse)
async def registrar_page(request: Request):
    return templates.TemplateResponse(request=request, name="registrar.html")

@app.post("/registrar")
async def registrar(request: Request):
    return RedirectResponse(url="/")

# ===================== SOLICITAÇÕES DE ACESSO =====================

@app.post("/api/acesso/solicitar")
async def solicitar_acesso(request: Request, nome: str = Form(...), email: str = Form(...), motivo: str = Form("")):
    try:
        supabase_admin.table("solicitacoes_acesso").insert({
            "nome": nome,
            "email": email,
            "motivo": motivo,
            "status": "pendente"
        }).execute()
        notificar_admins(
            f"Nova solicitação de acesso — {nome}",
            f"""<div style="font-family:sans-serif;max-width:600px;margin:0 auto;padding:24px">
              <h2 style="color:#6366f1">Nova Solicitação de Acesso</h2>
              <p><strong>Nome:</strong> {nome}</p>
              <p><strong>E-mail:</strong> {email}</p>
              <p><strong>Motivo:</strong> {motivo or 'Não informado'}</p>
              <p style="color:#888;font-size:12px">Acesse as Configurações do sistema para aprovar ou rejeitar.</p>
            </div>"""
        )
        return {"status": "enviado"}
    except Exception as e:
        print(f"Erro solicitar acesso: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/acesso/solicitacoes")
async def listar_solicitacoes(request: Request):
    token = request.cookies.get("token")
    role = request.cookies.get("role")
    if not token or role != "admin":
        raise HTTPException(status_code=403)
    try:
        resultado = supabase.table("solicitacoes_acesso").select("*").order("created_at", desc=True).execute()
        return resultado.data
    except Exception as e:
        print(f"Erro ao listar solicitações: {e}")
        return []

@app.post("/api/acesso/aprovar/{id}")
async def aprovar_acesso(id: str, request: Request, senha: str = Form(...)):
    token = request.cookies.get("token")
    role = request.cookies.get("role")
    if not token or role != "admin":
        raise HTTPException(status_code=403)
    try:
        sol = supabase.table("solicitacoes_acesso").select("*").eq("id", id).execute()
        if not sol.data:
            raise HTTPException(status_code=404, detail="Solicitação não encontrada")
        s = sol.data[0]
        res = supabase_admin.auth.admin.create_user({
            "email": s["email"],
            "password": senha,
            "email_confirm": True
        })
        supabase.table("perfis").insert({
            "id": str(res.user.id),
            "email": s["email"],
            "nome": s["nome"],
            "role": "colaborador",
            "ativo": True,
            "modulos": ["chamados"]
        }).execute()
        supabase.table("solicitacoes_acesso").update({"status": "aprovado"}).eq("id", id).execute()
        return {"status": "aprovado"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Erro aprovar acesso: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/acesso/rejeitar/{id}")
async def rejeitar_acesso(id: str, request: Request):
    token = request.cookies.get("token")
    role = request.cookies.get("role")
    if not token or role != "admin":
        raise HTTPException(status_code=403)
    supabase.table("solicitacoes_acesso").update({"status": "rejeitado"}).eq("id", id).execute()
    return {"status": "rejeitado"}

@app.post("/api/usuarios/criar")
async def criar_usuario(
    request: Request,
    nome: str = Form(...),
    email: str = Form(...),
    senha: str = Form(...),
    role: str = Form("colaborador")
):
    token = request.cookies.get("token")
    r = request.cookies.get("role")
    if not token or r != "admin":
        raise HTTPException(status_code=403)
    if len(senha) < 6:
        raise HTTPException(status_code=400, detail="Senha deve ter no mínimo 6 caracteres")
    try:
        res = supabase_admin.auth.admin.create_user({
            "email": email,
            "password": senha,
            "email_confirm": True
        })
        supabase.table("perfis").insert({
            "id": str(res.user.id),
            "email": email,
            "nome": nome,
            "role": role,
            "ativo": True,
            "modulos": ["chamados"]
        }).execute()
        return {"status": "criado", "id": str(res.user.id)}
    except Exception as e:
        print(f"Erro ao criar usuário: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/minha-senha")
async def alterar_minha_senha(request: Request, senha_atual: str = Form(...), nova_senha: str = Form(...)):
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=401)
    if len(nova_senha) < 6:
        raise HTTPException(status_code=400, detail="Nova senha deve ter no mínimo 6 caracteres")
    try:
        user = supabase.auth.get_user(token)
        email = user.user.email
        supabase.auth.sign_in_with_password({"email": email, "password": senha_atual})
        supabase_admin.auth.admin.update_user_by_id(str(user.user.id), {"password": nova_senha})
        return {"status": "alterada"}
    except Exception as e:
        print(f"Erro ao alterar senha: {e}")
        raise HTTPException(status_code=400, detail="Senha atual incorreta ou erro ao alterar")

@app.get("/alterar-senha", response_class=HTMLResponse)
async def alterar_senha_page(request: Request):
    token = request.cookies.get("token")
    if not token:
        return RedirectResponse(url="/")
    return templates.TemplateResponse(request=request, name="alterar_senha.html")

# ===================== API USUÁRIOS =====================

# Mantenha as duas rotas para o JS não dar 404
@app.get("/api/meu-email")
@app.get("/api/meu-perfil")
async def api_meu_perfil_unificada(request: Request):
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=401)
    try:
        res_user = supabase.auth.get_user(token)
        email = res_user.user.email
        
        res = supabase.table("perfis").select("*").eq("email", email).execute()
        
        # Se não achar no banco, envia um objeto básico para o JS não quebrar
        if not res.data:
            return {
                "email": email,
                "nome": "Usuário",
                "role": "colaborador",
                "modulos": ["ordens_servico"]
            }

        user = res.data[0]
        role = user.get("role", "colaborador")

        # Usa exatamente os módulos configurados no banco
        modulos = list(user.get("modulos") or [])
        # Admin sempre tem configuracoes; demais módulos são configurados individualmente
        if role == "admin":
            if "configuracoes" not in modulos:
                modulos.append("configuracoes")

        return {
            "email": email,
            "nome": user.get("nome") or "Colaborador Voo Suporte",
            "role": role,
            "modulos": modulos
        }
    except Exception as e:
        print(f"Erro no console: {e}")
        raise HTTPException(status_code=401)

@app.get("/api/usuarios")
async def api_usuarios(request: Request):
    token = request.cookies.get("token")
    role = request.cookies.get("role")
    if not token or role != "admin":
        raise HTTPException(status_code=403)
    # Garanta que o select tenha o "*" ou inclua explicitamente "telefone"
    resultado = supabase.table("perfis").select("*").order("nome").execute()
    return resultado.data

@app.post("/api/usuarios/{id}/perfil")
async def atualizar_perfil(id: str, request: Request, nome: str = Form(""), cargo: str = Form(""), telefone: str = Form(""), departamento_id: str = Form(""), modulos: str = Form("[]"), cpf: str = Form("")):
    token = request.cookies.get("token")
    role = request.cookies.get("role")
    if not token or role != "admin":
        raise HTTPException(status_code=403)
    import json
    modulos_list = json.loads(modulos)
    update_data = {"cargo": cargo, "modulos": modulos_list, "telefone": telefone}
    if nome:
        update_data["nome"] = nome
    if departamento_id:
        update_data["departamento_id"] = departamento_id
    else:
        update_data["departamento_id"] = None
    if cpf:
        update_data["cpf"] = cpf.replace(".", "").replace("-", "").strip()
    supabase.table("perfis").update(update_data).eq("id", id).execute()
    return {"status": "atualizado"}

@app.post("/api/usuarios/{id}/role")
async def alterar_role(id: str, request: Request, role: str = Form(...)):
    token = request.cookies.get("token")
    r = request.cookies.get("role")
    if not token or r != "admin":
        raise HTTPException(status_code=403)
    if role not in ["admin", "colaborador"]:
        raise HTTPException(status_code=400)
    supabase.table("perfis").update({"role": role}).eq("id", id).execute()
    return {"status": "atualizado"}

@app.post("/api/usuarios/{id}/status")
async def alterar_status(id: str, request: Request, ativo: str = Form(...)):
    token = request.cookies.get("token")
    role = request.cookies.get("role")
    if not token or role != "admin":
        raise HTTPException(status_code=403)
    supabase.table("perfis").update({"ativo": ativo == "true"}).eq("id", id).execute()
    return {"status": "atualizado"}

@app.post("/api/usuarios/{id}/senha")
async def alterar_senha(id: str, request: Request, nova_senha: str = Form(...)):
    token = request.cookies.get("token")
    role = request.cookies.get("role")
    if not token or role != "admin":
        raise HTTPException(status_code=403)
    if len(nova_senha) < 6:
        raise HTTPException(status_code=400, detail="Senha deve ter no mínimo 6 caracteres")
    try:
        supabase_admin.auth.admin.update_user_by_id(id, {"password": nova_senha})
        return {"status": "senha alterada"}
    except Exception as e:
        print(f"Erro ao alterar senha: {e}")
        raise HTTPException(status_code=500, detail="Erro ao alterar senha")

@app.delete("/api/usuarios/{id}")
async def excluir_usuario(id: str, request: Request):
    token = request.cookies.get("token")
    role = request.cookies.get("role")
    if not token or role != "admin":
        raise HTTPException(status_code=403)
    try:
        perfil = supabase.table("perfis").select("email").eq("id", id).execute()
        if not perfil.data:
            raise HTTPException(status_code=404, detail="Usuário não encontrado")
        email_usuario = perfil.data[0]["email"]
        chamados = supabase.table("chamados_controle").select("id").eq("colaborador_email", email_usuario).neq("status", "fechado").execute()
        if chamados.data:
            raise HTTPException(status_code=400, detail="Usuário possui chamados ativos. Encerre-os antes de excluir.")
        supabase.table("perfis").delete().eq("id", id).execute()
        supabase_admin.auth.admin.delete_user(id)
        return {"status": "excluido"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Erro ao excluir usuário: {e}")
        raise HTTPException(status_code=500, detail="Erro ao excluir usuário")

# ===================== API CLIENTES =====================



@app.get("/api/clientes")
async def api_clientes(request: Request):
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=401)
    resultado = supabase.table("clientes").select("*").eq("ativo", True).order("nome").execute()
    return resultado.data

@app.post("/api/clientes")
async def criar_cliente(request: Request, nome: str = Form(...), municipio: str = Form(...)):
    token = request.cookies.get("token")
    role = request.cookies.get("role")
    if not token or role != "admin":
        raise HTTPException(status_code=403)
    resultado = supabase.table("clientes").insert({"nome": nome, "municipio": municipio}).execute()
    return resultado.data[0]

@app.delete("/api/clientes/{id}")
async def deletar_cliente(id: str, request: Request):
    token = request.cookies.get("token")
    role = request.cookies.get("role")
    if not token or role != "admin":
        raise HTTPException(status_code=403)
    supabase.table("clientes").update({"ativo": False}).eq("id", id).execute()
    return {"status": "removido"}

# ===================== API PORTAL =====================

@app.get("/api/portal-stats")
async def portal_stats(request: Request):
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=401)
    try:
        user = supabase.auth.get_user(token)
        email = user.user.email
        role = request.cookies.get("role")
        if role == "admin":
            chamados_novos = supabase.table("chamados_controle").select("id").eq("status", "aberto").is_("qualitor_id", "null").execute()
            chamados_aguardando = supabase.table("chamados_controle").select("id").eq("status", "aguardando_colaborador").execute()
            chamados_respondidos = supabase.table("chamados_controle").select("id").eq("status", "pendente_dev").execute()
        else:
            chamados_novos = supabase.table("chamados_controle").select("id").eq("colaborador_email", email).eq("status", "aberto").execute()
            chamados_aguardando = supabase.table("chamados_controle").select("id").eq("colaborador_email", email).eq("status", "aguardando_colaborador").execute()
            chamados_respondidos = supabase.table("chamados_controle").select("id").eq("colaborador_email", email).eq("status", "pendente_dev").execute()
        os_pendentes = supabase.table("os_ordens").select("id").eq("colaborador_email", email).eq("status", "emitida").execute()
        os_prestacao = supabase.table("os_ordens").select("id").eq("colaborador_email", email).eq("status", "prestacao_devolvida").execute()
        return {
            "chamados_novos": len(chamados_novos.data),
            "chamados_aguardando": len(chamados_aguardando.data),
            "chamados_respondidos": len(chamados_respondidos.data),
            "os_pendentes": len(os_pendentes.data),
            "os_prestacao": len(os_prestacao.data)
        }
    except Exception as e:
        print(f"Erro portal stats: {e}")
        return {"chamados_novos": 0, "chamados_aguardando": 0, "chamados_respondidos": 0, "os_pendentes": 0, "os_prestacao": 0}

# ===================== API CHAMADOS =====================

@app.get("/api/meus-chamados")
async def api_meus_chamados(request: Request):
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=401)
    try:
        user = supabase.auth.get_user(token)
        email = user.user.email
        proprios = supabase.table("chamados_controle").select("*").eq("colaborador_email", email).execute()
        participacoes = supabase.table("chamados_participantes").select("chamado_id").eq("usuario_email", email).execute()
        ids_participante = [p["chamado_id"] for p in participacoes.data]
        chamados_participante = []
        if ids_participante:
            for cid in ids_participante:
                r = supabase.table("chamados_controle").select("*").eq("id", cid).execute()
                if r.data:
                    chamados_participante.extend(r.data)
        todos = proprios.data + [c for c in chamados_participante if c["id"] not in [x["id"] for x in proprios.data]]
        todos.sort(key=lambda x: x["created_at"], reverse=True)
        return todos
    except Exception as e:
        print(f"Erro: {e}")
        raise HTTPException(status_code=401)

@app.get("/api/chamados")
async def api_chamados(request: Request):
    token = request.cookies.get("token")
    role = request.cookies.get("role")
    if not token or (role != "admin" and not tem_modulo(request, "chamados_gestor")):
        raise HTTPException(status_code=403)
    resultado = supabase.table("chamados_controle").select("*").order("created_at", desc=True).execute()
    return resultado.data

@app.get("/api/chamados/{id}/historico")
async def api_historico(id: str, request: Request):
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=401)
    resultado = supabase.table("chamados_historico").select("*").eq("chamado_id", id).order("created_at").execute()
    return resultado.data

@app.get("/api/chamados/{id}/mensagens")
async def api_mensagens(id: str, request: Request):
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=401)
    resultado = supabase.table("chamados_mensagens").select("*").eq("chamado_id", id).order("created_at").execute()
    return resultado.data

@app.get("/api/chamados/{id}/participantes")
async def api_participantes(id: str, request: Request):
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=401)
    resultado = supabase.table("chamados_participantes").select("*").eq("chamado_id", id).execute()
    return resultado.data

@app.post("/api/chamados/{id}/participantes")
async def adicionar_participante(id: str, request: Request, usuario_email: str = Form(...)):
    token = request.cookies.get("token")
    role = request.cookies.get("role")
    if not token or role != "admin":
        raise HTTPException(status_code=403)
    user = supabase.auth.get_user(token)
    try:
        supabase.table("chamados_participantes").insert({
            "chamado_id": id,
            "usuario_email": usuario_email,
            "adicionado_por": user.user.email
        }).execute()
        registrar_historico(id, "participante_adicionado", f"{usuario_email} adicionado ao chamado", user.user.email)
        chamado = supabase.table("chamados_controle").select("*").eq("id", id).execute()
        if chamado.data:
            c = chamado.data[0]
            try:
                resend.Emails.send({
                    "from": "Voo Suporte <noreply@voosuporte.com.br>",
                    "to": usuario_email,
                    "subject": f"Você foi adicionado ao chamado {id[:8].upper()}",
                    "html": f"""<div style="font-family:sans-serif;max-width:600px;margin:0 auto;padding:24px">
                      <h2>Você foi adicionado a um chamado</h2>
                      <p>Chamado <strong>{id[:8].upper()}</strong> — {c['cliente_nome']}.</p>
                      <p style="color:#888;font-size:12px">Acesse o sistema para acompanhar.</p>
                    </div>"""
                })
            except Exception as e:
                print(f"Erro e-mail: {e}")
    except:
        raise HTTPException(status_code=400, detail="Usuário já é participante")
    return {"status": "adicionado"}

@app.delete("/api/chamados/{id}/participantes/{email}")
async def remover_participante(id: str, email: str, request: Request):
    token = request.cookies.get("token")
    role = request.cookies.get("role")
    if not token or role != "admin":
        raise HTTPException(status_code=403)
    supabase.table("chamados_participantes").delete().eq("chamado_id", id).eq("usuario_email", email).execute()
    return {"status": "removido"}

@app.post("/api/chamados/{id}/convidar-departamento")
async def convidar_departamento(id: str, request: Request, departamento_id: str = Form(...)):
    token = request.cookies.get("token")
    role = request.cookies.get("role")
    if not token or role != "admin":
        raise HTTPException(status_code=403)
    user = supabase.auth.get_user(token)
    # Busca todos os usuários do departamento
    usuarios = supabase.table("perfis").select("email,nome").eq("departamento_id", departamento_id).eq("ativo", True).execute()
    chamado_res = supabase.table("chamados_controle").select("*").eq("id", id).execute()
    c = chamado_res.data[0] if chamado_res.data else {}
    adicionados = []
    for u in (usuarios.data or []):
        try:
            # Verifica se já é participante
            existe = supabase.table("chamados_participantes").select("id").eq("chamado_id", id).eq("usuario_email", u["email"]).execute()
            if existe.data:
                continue
            supabase.table("chamados_participantes").insert({
                "chamado_id": id,
                "usuario_email": u["email"],
                "adicionado_por": user.user.email
            }).execute()
            adicionados.append(u["email"])
            # Notifica por e-mail
            try:
                resend.Emails.send({
                    "from": "Voo Suporte <noreply@voosuporte.com.br>",
                    "to": u["email"],
                    "subject": f"Você foi adicionado ao chamado {id[:8].upper()}",
                    "html": f"""<div style="font-family:sans-serif;max-width:600px;margin:0 auto;padding:24px">
                      <h2 style="color:#6366f1">Novo chamado compartilhado com você</h2>
                      <p>Chamado <strong>{id[:8].upper()}</strong> — {c.get('cliente_nome','')}.</p>
                      <p style="color:#888;font-size:12px">Acesse o sistema para acompanhar.</p>
                    </div>"""
                })
            except Exception as e:
                print(f"Erro e-mail depto: {e}")
        except Exception:
            continue
    if adicionados:
        registrar_historico(id, "participante_adicionado", f"Departamento convidado — {len(adicionados)} usuário(s)", user.user.email)
    return {"status": "ok", "adicionados": len(adicionados)}

@app.post("/chamado")
async def criar_chamado(
    request: Request,
    colaborador_email: str = Form(...),
    unidade: str = Form(...),
    cliente_nome: str = Form(...),
    link_url: str = Form(""),
    link_drive: str = Form(""),
    descricao_tecnica: str = Form(...),
    categoria: str = Form("outro"),
    prioridade: str = Form("media"),
    arquivos: list[UploadFile] = File(None)
):
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=401)
    if not arquivos or not any(a.filename for a in arquivos):
        raise HTTPException(status_code=400, detail="Anexo obrigatório")
    urls = []
    for arq in arquivos:
        if arq.filename:
            url = await fazer_upload(arq)
            if url:
                urls.append(url)
    import json as _json
    evidencia_url = urls[0] if urls else ""
    evidencia_urls_json = _json.dumps(urls) if urls else "[]"
    resultado = supabase.table("chamados_controle").insert({
        "colaborador_email": colaborador_email,
        "unidade": unidade,
        "cliente_nome": cliente_nome,
        "link_url": link_url,
        "link_drive": link_drive,
        "descricao_tecnica": descricao_tecnica,
        "evidencia_url": evidencia_url,
        "evidencia_urls": evidencia_urls_json,
        "categoria": categoria,
        "prioridade": prioridade,
        "status": "aberto"
    }).execute()
    chamado_id = resultado.data[0]["id"]
    registrar_historico(chamado_id, "aberto", f"Chamado aberto por {colaborador_email}", colaborador_email)
    # Salva primeira mensagem com TODOS os anexos e link drive
    msg_abertura = descricao_tecnica
    if link_drive:
        msg_abertura += f"\n\n🔗 Link de evidência: {link_drive}"
    supabase.table("chamados_mensagens").insert({
        "chamado_id": chamado_id,
        "autor_email": colaborador_email,
        "tipo": "abertura",
        "mensagem": msg_abertura,
        "evidencia_url": evidencia_url,
        "evidencia_urls": evidencia_urls_json
    }).execute()
    prioridade_label = {"baixa": "🟢 Baixa", "media": "🟡 Média", "alta": "🔴 Alta", "urgente": "🚨 Urgente"}.get(prioridade, prioridade)
    categoria_label = {"erro_sistema": "Erro de sistema", "acesso": "Acesso", "lentidao": "Lentidão", "duvida": "Dúvida", "implantacao": "Implantação", "outro": "Outro"}.get(categoria, categoria)
    notificar_admins(
        f"🆕 Novo chamado — {unidade} [{prioridade_label}]",
        f"""<div style="font-family:sans-serif;max-width:600px;margin:0 auto;padding:24px">
          <h2>Novo chamado aberto</h2>
          <table style="width:100%;border-collapse:collapse;margin-bottom:16px">
            <tr><td style="padding:6px 0;color:#888;font-size:12px;width:120px">Colaborador</td><td style="font-size:13px">{colaborador_email}</td></tr>
            <tr><td style="padding:6px 0;color:#888;font-size:12px">Município</td><td style="font-size:13px">{cliente_nome}</td></tr>
            <tr><td style="padding:6px 0;color:#888;font-size:12px">Unidade</td><td style="font-size:13px">{unidade}</td></tr>
            <tr><td style="padding:6px 0;color:#888;font-size:12px">Categoria</td><td style="font-size:13px">{categoria_label}</td></tr>
            <tr><td style="padding:6px 0;color:#888;font-size:12px">Prioridade</td><td style="font-size:13px">{prioridade_label}</td></tr>
            <tr><td style="padding:6px 0;color:#888;font-size:12px">Anexos</td><td style="font-size:13px">{len(urls)} arquivo(s)</td></tr>
          </table>
          <div style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:8px;padding:14px;margin-bottom:16px">
            <p style="font-size:13px;color:#111;line-height:1.6;margin:0">{descricao_tecnica}</p>
          </div>
          <p style="color:#888;font-size:12px">Acesse o sistema para vincular o Qualitor e acompanhar.</p>
        </div>"""
    )
    return JSONResponse({"id": chamado_id, "status": "registrado"})

@app.post("/chamado/{id}/editar")
async def editar_chamado(id: str, request: Request, unidade: str = Form(...), cliente_nome: str = Form(...), descricao_tecnica: str = Form(...)):
    token = request.cookies.get("token")
    role = request.cookies.get("role")
    if not token or role != "admin":
        raise HTTPException(status_code=403)
    user = supabase.auth.get_user(token)
    chamado_atual = supabase.table("chamados_controle").select("descricao_tecnica,unidade,cliente_nome").eq("id", id).execute()
    if chamado_atual.data:
        c = chamado_atual.data[0]
        historico_desc = f"Versão anterior — Município: {c['cliente_nome']} | Unidade: {c['unidade']} | Descrição: {c['descricao_tecnica'][:100]}"
        registrar_historico(id, "editado", historico_desc, user.user.email)
    supabase.table("chamados_controle").update({"unidade": unidade, "cliente_nome": cliente_nome, "descricao_tecnica": descricao_tecnica}).eq("id", id).execute()
    return {"status": "editado"}

@app.delete("/chamado/{id}")
async def excluir_chamado(id: str, request: Request):
    token = request.cookies.get("token")
    role = request.cookies.get("role")
    if not token or role != "admin":
        raise HTTPException(status_code=403)
    supabase.table("chamados_participantes").delete().eq("chamado_id", id).execute()
    supabase.table("chamados_historico").delete().eq("chamado_id", id).execute()
    supabase.table("chamados_mensagens").delete().eq("chamado_id", id).execute()
    supabase.table("chamados_controle").delete().eq("id", id).execute()
    return {"status": "excluido"}

@app.post("/chamado/{id}/reabrir")
async def reabrir_chamado(id: str, request: Request):
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=401)
    user = supabase.auth.get_user(token)
    supabase.table("chamados_controle").update({"status": "aberto", "ultima_interacao": "now()"}).eq("id", id).execute()
    registrar_historico(id, "reaberto", "Chamado reaberto", user.user.email)
    return {"status": "reaberto"}

@app.post("/chamado/{id}/qualitor")
async def vincular_qualitor(id: str, request: Request, qualitor_id: str = Form(...)):
    token = request.cookies.get("token")
    role = request.cookies.get("role")
    if not token or role != "admin":
        raise HTTPException(status_code=403)
    user = supabase.auth.get_user(token)
    supabase.table("chamados_controle").update({"qualitor_id": qualitor_id, "status": "em_analise"}).eq("id", id).execute()
    registrar_historico(id, "qualitor_vinculado", f"ID Qualitor {qualitor_id} vinculado", user.user.email)
    return {"status": "vinculado"}

@app.post("/chamado/{id}/sla")
async def atualizar_sla(id: str, request: Request, sla_horas: int = Form(...)):
    token = request.cookies.get("token")
    role = request.cookies.get("role")
    if not token or role != "admin":
        raise HTTPException(status_code=403)
    supabase.table("chamados_controle").update({"sla_horas": sla_horas}).eq("id", id).execute()
    return {"status": "atualizado"}

@app.post("/chamado/{id}/status")
async def alterar_status(id: str, request: Request, status: str = Form(...)):
    token = request.cookies.get("token")
    role = request.cookies.get("role")
    if not token or (role != "admin" and not tem_modulo(request, "chamados_gestor")):
        raise HTTPException(status_code=403)
    user = supabase.auth.get_user(token)
    status_validos = ["aberto", "em_analise", "aguardando_colaborador", "pendente_dev", "em_correcao", "fechado", "sla_vencido"]
    if status not in status_validos:
        raise HTTPException(status_code=400, detail="Status inválido")
    supabase.table("chamados_controle").update({"status": status, "ultima_interacao": "now()"}).eq("id", id).execute()
    registrar_historico(id, status, f"Status alterado para: {status}", user.user.email)
    # Notifica colaborador por e-mail sobre a mudança de status
    status_labels = {
        "aberto": ("🔵 Chamado reaberto", "#eff6ff", "#bfdbfe", "#1e3a5f"),
        "em_analise": ("🔍 Chamado em análise", "#f0f9ff", "#bae6fd", "#0c4a6e"),
        "aguardando_colaborador": ("⚠️ Aguardando informações", "#fef3c7", "#fcd34d", "#92400e"),
        "pendente_dev": ("⏳ Aguardando desenvolvimento", "#f5f3ff", "#ddd6fe", "#4c1d95"),
        "em_correcao": ("🔧 Em correção", "#fff7ed", "#fed7aa", "#7c2d12"),
        "fechado": ("✅ Chamado encerrado", "#f0fdf4", "#bbf7d0", "#14532d"),
        "sla_vencido": ("🔴 SLA vencido", "#fef2f2", "#fecaca", "#7f1d1d"),
    }
    try:
        chamado_res = supabase.table("chamados_controle").select("colaborador_email,cliente_nome,titulo,descricao").eq("id", id).execute()
        if chamado_res.data:
            c = chamado_res.data[0]
            if c.get("colaborador_email") and status in status_labels:
                titulo_email, bg, borda, cor_txt = status_labels[status]
                resend.Emails.send({
                    "from": "Voo Suporte <noreply@voosuporte.com.br>",
                    "to": c["colaborador_email"],
                    "subject": f"{titulo_email} — {id[:8].upper()}",
                    "html": f"""<div style="font-family:sans-serif;max-width:600px;margin:0 auto;padding:24px;background:#fff;border-radius:12px">
  <div style="background:{bg};border:1px solid {borda};border-radius:10px;padding:16px 20px;margin-bottom:20px">
    <p style="color:{cor_txt};font-size:15px;font-weight:600;margin:0">{titulo_email}</p>
  </div>
  <table style="width:100%;border-collapse:collapse;margin-bottom:20px">
    <tr><td style="padding:8px 0;color:#6b7280;font-size:13px;width:130px">Chamado</td><td style="padding:8px 0;font-size:13px;font-weight:500;font-family:monospace">{id[:8].upper()}</td></tr>
    <tr style="border-top:1px solid #f3f4f6"><td style="padding:8px 0;color:#6b7280;font-size:13px">Município</td><td style="padding:8px 0;font-size:13px">{c.get('cliente_nome','')}</td></tr>
    {"<tr style='border-top:1px solid #f3f4f6'><td style='padding:8px 0;color:#6b7280;font-size:13px'>Título</td><td style='padding:8px 0;font-size:13px'>" + (c.get('titulo','') or c.get('descricao','')[:60]) + "</td></tr>" if c.get('titulo') else ""}
    <tr style="border-top:1px solid #f3f4f6"><td style="padding:8px 0;color:#6b7280;font-size:13px">Atualizado por</td><td style="padding:8px 0;font-size:13px">{user.user.email}</td></tr>
  </table>
  <p style="color:#9ca3af;font-size:12px;margin:0">Acesse o sistema Voo Suporte para mais detalhes.</p>
</div>"""
                })
    except Exception as e:
        print(f"Erro e-mail status: {e}")
    return {"status": "atualizado"}

@app.post("/chamado/{id}/mensagem")
async def enviar_mensagem_admin(id: str, request: Request, texto: str = Form(...), tipo: str = Form("interno"), arquivo: UploadFile = File(None)):
    import json as _json
    token = request.cookies.get("token")
    role = request.cookies.get("role")
    if not token or (role != "admin" and not tem_modulo(request, "chamados_gestor")):
        raise HTTPException(status_code=403)
    user = supabase.auth.get_user(token)
    chamado = supabase.table("chamados_controle").select("*").eq("id", id).execute()
    if not chamado.data:
        raise HTTPException(status_code=404)
    c = chamado.data[0]
    evidencia_url = ""
    if arquivo and arquivo.filename:
        evidencia_url = await fazer_upload(arquivo) or ""
    evidencia_urls_json = _json.dumps([evidencia_url]) if evidencia_url else "[]"
    # Atualiza status conforme tipo
    novo_status = None
    if tipo == "pedido_info":
        novo_status = "aguardando_colaborador"
    elif tipo == "parceiro":
        novo_status = "pendente_dev"
    if novo_status:
        supabase.table("chamados_controle").update({"status": novo_status, "ultima_interacao": "now()"}).eq("id", id).execute()
    else:
        supabase.table("chamados_controle").update({"ultima_interacao": "now()"}).eq("id", id).execute()
    supabase.table("chamados_mensagens").insert({
        "chamado_id": id,
        "autor_email": user.user.email,
        "tipo": tipo,
        "mensagem": texto,
        "evidencia_url": evidencia_url,
        "evidencia_urls": evidencia_urls_json
    }).execute()
    registrar_historico(id, f"mensagem_{tipo}", f"Mensagem {tipo}: {texto[:80]}", user.user.email)
    # Notifica colaborador se for parceiro ou pedido_info
    if tipo in ("parceiro", "pedido_info") and c.get("colaborador_email"):
        assunto = "✅ Resposta recebida" if tipo == "parceiro" else "⚠️ Informações necessárias"
        cor = "#f0fdf4" if tipo == "parceiro" else "#fef3c7"
        cor_borda = "#86efac" if tipo == "parceiro" else "#fcd34d"
        cor_texto = "#14532d" if tipo == "parceiro" else "#92400e"
        try:
            resend.Emails.send({
                "from": "Voo Suporte <noreply@voosuporte.com.br>",
                "to": c["colaborador_email"],
                "subject": f"{assunto} — Chamado {id[:8].upper()}",
                "html": f"""<div style="font-family:sans-serif;max-width:600px;margin:0 auto;padding:24px">
                  <h2>{assunto} — {id[:8].upper()}</h2>
                  <p>Município: {c.get('cliente_nome','')}</p>
                  <div style="background:{cor};border:1px solid {cor_borda};border-radius:8px;padding:16px;margin-bottom:16px">
                    <p style="color:{cor_texto};margin:0">{texto}</p>
                  </div>
                  <p style="color:#888;font-size:12px">Acesse o sistema para responder.</p>
                </div>"""
            })
        except Exception as e:
            print(f"Erro e-mail: {e}")
    return {"status": "enviado"}

@app.post("/chamado/{id}/pedir-info")
async def pedir_info(id: str, request: Request, mensagem: str = Form(...)):
    token = request.cookies.get("token")
    role = request.cookies.get("role")
    if not token or role != "admin":
        raise HTTPException(status_code=403)
    chamado = supabase.table("chamados_controle").select("*").eq("id", id).execute()
    if not chamado.data:
        raise HTTPException(status_code=404)
    c = chamado.data[0]
    user = supabase.auth.get_user(token)
    supabase.table("chamados_controle").update({"status": "aguardando_colaborador", "ultima_interacao": "now()"}).eq("id", id).execute()
    supabase.table("chamados_mensagens").insert({"chamado_id": id, "autor_email": user.user.email, "tipo": "pedido_info", "mensagem": mensagem, "evidencia_url": ""}).execute()
    registrar_historico(id, "pedido_info", f"Informações solicitadas: {mensagem[:80]}", user.user.email)
    try:
        resend.Emails.send({
            "from": "Voo Suporte <noreply@voosuporte.com.br>",
            "to": c["colaborador_email"],
            "subject": f"⚠️ Informações necessárias — Chamado {id[:8].upper()}",
            "html": f"""<div style="font-family:sans-serif;max-width:600px;margin:0 auto;padding:24px">
              <h2>Informações adicionais necessárias</h2>
              <p>Chamado <strong>{id[:8].upper()}</strong> — {c['cliente_nome']}.</p>
              <div style="background:#fef3c7;border:1px solid #fcd34d;border-radius:8px;padding:16px;margin-bottom:16px">
                <p style="color:#92400e;margin:0">{mensagem}</p>
              </div>
              <p style="color:#888;font-size:12px">Acesse o sistema e complemente seu chamado.</p>
            </div>"""
        })
    except Exception as e:
        print(f"Erro e-mail: {e}")
    return {"status": "solicitado"}

@app.post("/chamado/{id}/complementar")
async def complementar_chamado(id: str, request: Request, mensagem: str = Form(...), arquivo: UploadFile = File(None)):
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=401)
    user = supabase.auth.get_user(token)
    evidencia_url = await fazer_upload(arquivo)
    supabase.table("chamados_controle").update({"status": "em_analise", "ultima_interacao": "now()"}).eq("id", id).execute()
    supabase.table("chamados_mensagens").insert({"chamado_id": id, "autor_email": user.user.email, "tipo": "complemento", "mensagem": mensagem, "evidencia_url": evidencia_url}).execute()
    registrar_historico(id, "complementado", f"Complemento enviado: {mensagem[:80]}", user.user.email)
    return {"status": "complementado"}

@app.post("/chamado/{id}/resposta")
async def salvar_resposta(id: str, request: Request, resposta: str = Form(...), arquivo: UploadFile = File(None)):
    token = request.cookies.get("token")
    role = request.cookies.get("role")
    if not token or role != "admin":
        raise HTTPException(status_code=403)
    chamado = supabase.table("chamados_controle").select("*").eq("id", id).execute()
    if not chamado.data:
        raise HTTPException(status_code=404)
    c = chamado.data[0]
    user = supabase.auth.get_user(token)
    evidencia_url = await fazer_upload(arquivo)
    supabase.table("chamados_controle").update({"resposta_parceiro": resposta, "status": "pendente_dev", "ultima_interacao": "now()"}).eq("id", id).execute()
    supabase.table("chamados_mensagens").insert({"chamado_id": id, "autor_email": user.user.email, "tipo": "resposta", "mensagem": resposta, "evidencia_url": evidencia_url}).execute()
    registrar_historico(id, "resposta_recebida", "Resposta do parceiro registrada", user.user.email)
    destinatarios = [c["colaborador_email"]]
    participantes = supabase.table("chamados_participantes").select("usuario_email").eq("chamado_id", id).execute()
    for p in participantes.data:
        if p["usuario_email"] not in destinatarios:
            destinatarios.append(p["usuario_email"])
    for dest in destinatarios:
        try:
            resend.Emails.send({
                "from": "Voo Suporte <noreply@voosuporte.com.br>",
                "to": dest,
                "subject": f"✅ Resposta recebida — Chamado {id[:8].upper()}",
                "html": f"""<div style="font-family:sans-serif;max-width:600px;margin:0 auto;padding:24px">
                  <h2>Resposta recebida — {id[:8].upper()}</h2>
                  <p>Cliente: {c['cliente_nome']}</p>
                  <div style="background:#f0faf5;border:1px solid #a8dfc3;border-radius:8px;padding:16px">
                    <p style="margin:0">{resposta}</p>
                  </div>
                  <p style="color:#888;font-size:12px;margin-top:12px">Acesse o sistema para ver os detalhes.</p>
                </div>"""
            })
        except Exception as e:
            print(f"Erro e-mail: {e}")
    return {"status": "salvo"}

@app.post("/chamado/{id}/fechar")
async def fechar_chamado(id: str, request: Request):
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=401)
    user = supabase.auth.get_user(token)
    supabase.table("chamados_controle").update({"status": "fechado"}).eq("id", id).execute()
    registrar_historico(id, "fechado", "Chamado marcado como resolvido", user.user.email)
    return {"status": "fechado"}

@app.get("/api/busca")
async def busca_global(q: str, request: Request):
    token = request.cookies.get("token")
    role = request.cookies.get("role")
    if not token or role != "admin":
        raise HTTPException(status_code=403)
    q = q.lower().strip()
    if len(q) < 2:
        return []
    chamados = supabase.table("chamados_controle").select("*").order("created_at", desc=True).execute()
    mensagens = supabase.table("chamados_mensagens").select("*").execute()
    ids_com_msg = set()
    for m in mensagens.data:
        if q in (m.get("mensagem") or "").lower():
            ids_com_msg.add(m["chamado_id"])
    resultado = []
    for c in chamados.data:
        match = (
            q in (c.get("descricao_tecnica") or "").lower() or
            q in (c.get("cliente_nome") or "").lower() or
            q in (c.get("unidade") or "").lower() or
            q in (c.get("colaborador_email") or "").lower() or
            q in (c.get("qualitor_id") or "").lower() or
            q in c["id"].lower() or
            c["id"] in ids_com_msg
        )
        if match:
            resultado.append(c)
    return resultado

@app.get("/api/notificacoes")
async def api_notificacoes(request: Request):
    token = request.cookies.get("token")
    role = request.cookies.get("role")
    if not token:
        raise HTTPException(status_code=401)
    try:
        if role == "admin":
            novos = supabase.table("chamados_controle").select("id,created_at,unidade,cliente_nome").eq("status", "aberto").is_("qualitor_id", "null").execute()
            return {
                "total": len(novos.data),
                "itens": [{"id": c["id"][:8].upper(), "texto": f"Novo chamado — {c['cliente_nome']}"} for c in novos.data[:5]]
            }
        else:
            user = supabase.auth.get_user(token)
            email = user.user.email
            aguardando = supabase.table("chamados_controle").select("id,cliente_nome").eq("colaborador_email", email).eq("status", "aguardando_colaborador").execute()
            respondidos = supabase.table("chamados_controle").select("id,cliente_nome").eq("colaborador_email", email).eq("status", "pendente_dev").execute()
            itens = []
            for c in aguardando.data[:3]:
                itens.append({"id": c["id"][:8].upper(), "texto": f"Sua resposta é necessária — {c['cliente_nome']}"})
            for c in respondidos.data[:3]:
                itens.append({"id": c["id"][:8].upper(), "texto": f"Resposta recebida — {c['cliente_nome']}"})
            return {"total": len(aguardando.data) + len(respondidos.data), "itens": itens}
    except Exception as e:
        print(f"Erro notificacoes: {e}")
        return {"total": 0, "itens": []}

@app.get("/api/relatorio-semanal")
async def relatorio_semanal(request: Request):
    token = request.cookies.get("token")
    role = request.cookies.get("role")
    if not token or role != "admin":
        raise HTTPException(status_code=403)
    try:
        chamados = supabase.table("chamados_controle").select("*").execute()
        total = len(chamados.data)
        abertos = len([c for c in chamados.data if c["status"] == "aberto"])
        pendentes = len([c for c in chamados.data if c["status"] == "pendente_dev"])
        fechados = len([c for c in chamados.data if c["status"] == "fechado"])
        sla_vencidos = 0
        for c in chamados.data:
            if c["status"] != "fechado":
                try:
                    dt_str = (c.get("ultima_interacao") or c["created_at"]).replace("Z", "+00:00")
                    h = (datetime.now(timezone.utc) - datetime.fromisoformat(dt_str)).total_seconds() / 3600
                    if h > (c.get("sla_horas") or 48):
                        sla_vencidos += 1
                except:
                    pass
        html = f"""<div style="font-family:sans-serif;max-width:600px;margin:0 auto;padding:24px">
          <h2 style="color:#6366f1">📊 Relatório Semanal — Suporte Técnico</h2>
          <p style="color:#888">Semana encerrada em {datetime.now(timezone.utc).strftime('%d/%m/%Y')}</p>
          <table style="width:100%;border-collapse:collapse;margin:20px 0">
            <tr style="background:#f9fafb"><td style="padding:12px;border:1px solid #e5e7eb;font-weight:600">Total de chamados</td><td style="padding:12px;border:1px solid #e5e7eb;text-align:center;font-size:18px;font-weight:700">{total}</td></tr>
            <tr><td style="padding:12px;border:1px solid #e5e7eb">🆕 Abertos / sem Qualitor</td><td style="padding:12px;border:1px solid #e5e7eb;text-align:center;color:#6366f1;font-weight:600">{abertos}</td></tr>
            <tr style="background:#f9fafb"><td style="padding:12px;border:1px solid #e5e7eb">✅ Respondidos pelo parceiro</td><td style="padding:12px;border:1px solid #e5e7eb;text-align:center;color:#d97706;font-weight:600">{pendentes}</td></tr>
            <tr><td style="padding:12px;border:1px solid #e5e7eb">✔ Encerrados</td><td style="padding:12px;border:1px solid #e5e7eb;text-align:center;color:#059669;font-weight:600">{fechados}</td></tr>
            <tr style="background:#fef2f2"><td style="padding:12px;border:1px solid #e5e7eb">⚠️ SLA vencido</td><td style="padding:12px;border:1px solid #e5e7eb;text-align:center;color:#dc2626;font-weight:600">{sla_vencidos}</td></tr>
          </table>
          <p style="color:#888;font-size:12px">Acesse o sistema para mais detalhes.</p>
        </div>"""
        notificar_admins("📊 Relatório Semanal — Suporte Técnico", html)
        return {"status": "enviado", "total": total, "abertos": abertos, "pendentes": pendentes, "fechados": fechados, "sla_vencidos": sla_vencidos}
    except Exception as e:
        print(f"Erro relatorio: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/relatorio-semanal-cron")
async def relatorio_semanal_cron(chave: str):
    if chave != "suporte2024cron":
        raise HTTPException(status_code=403)
    try:
        chamados = supabase.table("chamados_controle").select("*").execute()
        total = len(chamados.data)
        abertos = len([c for c in chamados.data if c["status"] == "aberto"])
        pendentes = len([c for c in chamados.data if c["status"] == "pendente_dev"])
        fechados = len([c for c in chamados.data if c["status"] == "fechado"])
        sla_vencidos = 0
        for c in chamados.data:
            if c["status"] != "fechado":
                try:
                    dt_str = (c.get("ultima_interacao") or c["created_at"]).replace("Z", "+00:00")
                    h = (datetime.now(timezone.utc) - datetime.fromisoformat(dt_str)).total_seconds() / 3600
                    if h > (c.get("sla_horas") or 48):
                        sla_vencidos += 1
                except:
                    pass
        html = f"""<div style="font-family:sans-serif;max-width:600px;margin:0 auto;padding:24px">
          <h2 style="color:#6366f1">📊 Relatório Semanal — Suporte Técnico</h2>
          <p style="color:#888">Semana encerrada em {datetime.now(timezone.utc).strftime('%d/%m/%Y')}</p>
          <table style="width:100%;border-collapse:collapse;margin:20px 0">
            <tr style="background:#f9fafb"><td style="padding:12px;border:1px solid #e5e7eb;font-weight:600">Total de chamados</td><td style="padding:12px;border:1px solid #e5e7eb;text-align:center;font-size:18px;font-weight:700">{total}</td></tr>
            <tr><td style="padding:12px;border:1px solid #e5e7eb">🆕 Abertos / sem Qualitor</td><td style="padding:12px;border:1px solid #e5e7eb;text-align:center;color:#6366f1;font-weight:600">{abertos}</td></tr>
            <tr style="background:#f9fafb"><td style="padding:12px;border:1px solid #e5e7eb">✅ Respondidos pelo parceiro</td><td style="padding:12px;border:1px solid #e5e7eb;text-align:center;color:#d97706;font-weight:600">{pendentes}</td></tr>
            <tr><td style="padding:12px;border:1px solid #e5e7eb">✔ Encerrados</td><td style="padding:12px;border:1px solid #e5e7eb;text-align:center;color:#059669;font-weight:600">{fechados}</td></tr>
            <tr style="background:#fef2f2"><td style="padding:12px;border:1px solid #e5e7eb">⚠️ SLA vencido</td><td style="padding:12px;border:1px solid #e5e7eb;text-align:center;color:#dc2626;font-weight:600">{sla_vencidos}</td></tr>
          </table>
          <p style="color:#888;font-size:12px">Acesse o sistema para mais detalhes.</p>
        </div>"""
        notificar_admins("📊 Relatório Semanal — Suporte Técnico", html)
        return {"status": "enviado"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===================== API VEÍCULOS =====================

@app.get("/api/os/veiculos")
async def api_os_veiculos(request: Request):
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=401)
    resultado = supabase.table("os_veiculos").select("*").eq("ativo", True).order("nome").execute()
    return resultado.data

@app.post("/api/os/veiculos")
async def criar_os_veiculo(
    request: Request,
    nome: str = Form(...),
    marca: str = Form(...),
    modelo: str = Form(...),
    placa: str = Form(""),
    tipo: str = Form(...),
    proprietario: str = Form(...)
):
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=401)
    try:
        resultado = supabase.table("os_veiculos").insert({
            "nome": nome,
            "marca": marca,
            "modelo": modelo,
            "placa": placa or None,
            "tipo": tipo,
            "proprietario": proprietario
        }).execute()
        return resultado.data[0]
    except Exception as e:
        print(f"Erro ao cadastrar veículo: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/os/veiculos/{id}")
async def deletar_os_veiculo(id: str, request: Request):
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=401)
    supabase.table("os_veiculos").update({"ativo": False}).eq("id", id).execute()
    return {"status": "removido"}

# ===================== MÓDULO O.S =====================

@app.get("/api/os/departamentos")
async def api_os_departamentos(request: Request):
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=401)
    resultado = supabase.table("os_departamentos").select("*").eq("ativo", True).order("nome").execute()
    return resultado.data

@app.post("/api/os/departamentos")
async def criar_os_departamento(request: Request, nome: str = Form(...), valor_diaria: float = Form(...), valor_meia_diaria: float = Form(...)):
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=401)
    resultado = supabase.table("os_departamentos").insert({
        "nome": nome,
        "valor_diaria": valor_diaria,
        "valor_meia_diaria": valor_meia_diaria
    }).execute()
    return resultado.data[0]

@app.delete("/api/os/departamentos/{id}")
async def deletar_os_departamento(id: str, request: Request):
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=401)
    supabase.table("os_departamentos").update({"ativo": False}).eq("id", id).execute()
    return {"status": "removido"}

@app.get("/api/os/municipios")
async def api_os_municipios(request: Request):
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=401)
    resultado = supabase.table("clientes").select("*").eq("ativo", True).order("nome").execute()
    return resultado.data

@app.post("/api/os/municipios")
async def criar_os_municipio(request: Request, nome: str = Form(...), estado: str = Form(...), distancia_km: float = Form(...)):
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=401)
    
    # 1. VERIFICAÇÃO DE DUPLICIDADE (Busca insensível a maiúsculas/minúsculas)
    existente = supabase.table("clientes").select("id").ilike("nome", nome).eq("estado", estado).eq("ativo", True).execute()
    if existente.data:
        raise HTTPException(status_code=400, detail=f"O município '{nome} - {estado}' já está cadastrado!")

    # 2. SE NÃO EXISTIR, INSERE NO BANCO
    resultado = supabase.table("clientes").insert({
        "nome": nome,
        "municipio": nome,
        "estado": estado,
        "distancia_km": distancia_km
    }).execute()
    return resultado.data[0]

@app.delete("/api/os/municipios/{id}")
async def deletar_os_municipio(id: str, request: Request):
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=401)
    supabase.table("clientes").update({"ativo": False}).eq("id", id).execute()
    return {"status": "removido"}

@app.get("/api/os/tipos-transporte")
async def api_os_tipos_transporte(request: Request):
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=401)
    resultado = supabase.table("os_tipos_transporte").select("*").eq("ativo", True).order("nome").execute()
    return resultado.data

@app.post("/api/os/tipos-transporte")
async def criar_os_tipo_transporte(request: Request, nome: str = Form(...)):
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=401)
    resultado = supabase.table("os_tipos_transporte").insert({"nome": nome}).execute()
    return resultado.data[0]

@app.delete("/api/os/tipos-transporte/{id}")
async def deletar_os_tipo_transporte(id: str, request: Request):
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=401)
    supabase.table("os_tipos_transporte").update({"ativo": False}).eq("id", id).execute()
    return {"status": "removido"}

@app.get("/api/os/tipos-adiantamento")
async def api_os_tipos_adiantamento(request: Request):
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=401)
    resultado = supabase.table("os_tipos_adiantamento").select("*").eq("ativo", True).order("nome").execute()
    return resultado.data

@app.post("/api/os/tipos-adiantamento")
async def criar_os_tipo_adiantamento(request: Request, nome: str = Form(...)):
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=401)
    resultado = supabase.table("os_tipos_adiantamento").insert({"nome": nome}).execute()
    return resultado.data[0]

@app.delete("/api/os/tipos-adiantamento/{id}")
async def deletar_os_tipo_adiantamento(id: str, request: Request):
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=401)
    supabase.table("os_tipos_adiantamento").update({"ativo": False}).eq("id", id).execute()
    return {"status": "removido"}

@app.get("/api/os/proximo-numero")
async def proximo_numero_os(request: Request):
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=401)
    ano = datetime.now(timezone.utc).year
    seq = supabase.table("os_sequencia").select("*").eq("ano", ano).execute()
    if seq.data:
        novo = seq.data[0]["ultimo_numero"] + 1
        supabase.table("os_sequencia").update({"ultimo_numero": novo}).eq("ano", ano).execute()
    else:
        novo = 1
        supabase.table("os_sequencia").insert({"ano": ano, "ultimo_numero": 1}).execute()
    return {"numero": f"{str(novo).zfill(3)}/{ano}"}

@app.get("/api/os/proximo-numero-preview")
async def proximo_numero_preview(request: Request):
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=401)
    ano = datetime.now(timezone.utc).year
    seq = supabase.table("os_sequencia").select("*").eq("ano", ano).execute()
    if seq.data:
        proximo = seq.data[0]["ultimo_numero"] + 1
    else:
        proximo = 1
    return {"numero": f"{str(proximo).zfill(3)}/{ano}"}

@app.post("/api/os/sequencia")
async def configurar_sequencia(request: Request, numero: int = Form(...)):
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=401)
    ano = datetime.now(timezone.utc).year
    seq = supabase.table("os_sequencia").select("*").eq("ano", ano).execute()
    if seq.data:
        supabase.table("os_sequencia").update({"ultimo_numero": numero - 1}).eq("ano", ano).execute()
    else:
        supabase.table("os_sequencia").insert({"ano": ano, "ultimo_numero": numero - 1}).execute()
    return {"status": "configurado", "proximo": f"{str(numero).zfill(3)}/{ano}"}

@app.get("/api/os/colaboradores")
async def api_os_colaboradores(request: Request):
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=401)
    resultado = supabase.table("perfis").select("*").eq("ativo", True).order("nome").execute()
    return resultado.data

@app.get("/api/os/ordens")
@app.get("/api/ordens")
async def listar_todas_ordens(request: Request, meu: int = 0, status: str = None):
    token = request.cookies.get("token")
    if not token: raise HTTPException(status_code=401)
    
    query = supabase.table("os_ordens").select("*, clientes(nome, estado), os_departamentos(nome)")
    
    # Filtra pelo status que o Financeiro enviar (ex: prestacao_enviada)
    if status:
        query = query.eq("status", status)
    
    if meu == 1:
        user_auth = supabase.auth.get_user(token)
        query = query.eq("colaborador_email", user_auth.user.email)
    
    resultado = query.order("created_at", desc=True).execute()
    ordens = resultado.data
    # Enriquece com adiantamentos de cada O.S (busca em lote para evitar N+1)
    if ordens:
        ids = [o["id"] for o in ordens]
        try:
            adiant_res = supabase.table("os_adiantamentos").select("*").in_("os_id", ids).execute()
            adiant_por_os = {}
            for a in (adiant_res.data or []):
                adiant_por_os.setdefault(a["os_id"], []).append(a)
            for o in ordens:
                o["adiantamentos"] = adiant_por_os.get(o["id"], [])
        except Exception as e:
            print(f"Erro ao buscar adiantamentos: {e}")
            for o in ordens:
                o["adiantamentos"] = []
    return ordens

@app.post("/api/os/ordens")
async def criar_ordem(request: Request, dados: dict):
    # O JavaScript envia um JSON. Use dados.get('campo') para capturar
    novo_numero = gerar_proximo_numero_os() # Sua função de sequência
    
    payload = {
        "numero": novo_numero,
        "colaborador_email": dados.get("colaborador_email"),
        "municipio_id": dados.get("municipio_id"),
        "departamento_id": dados.get("departamento_id"),
        "status": "pendente",
        "criado_em": datetime.now().isoformat(),
        # ... outros campos do seu dicionário 'dados'
    }
    
    res = supabase.table("os_ordens").insert(payload).execute()
    return res.data[0]

@app.post("/api/os/ordens/{id}/aprovar")
async def aprovar_os_ordem(id: str, request: Request):
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=401)
    user = supabase.auth.get_user(token)
    supabase.table("os_ordens").update({
        "status": "aprovada",
        "aprovado_por": user.user.email,
        "aprovado_em": datetime.now(timezone.utc).isoformat()
    }).eq("id", id).execute()
    try:
        os_data = supabase.table("os_ordens").select("*,clientes(nome)").eq("id", id).execute()
        if os_data.data:
            o = os_data.data[0]
            municipio = (o.get("clientes") or {}).get("nome", "—")
            resend.Emails.send({
                "from": "Voo Suporte <noreply@voosuporte.com.br>",
                "to": o["colaborador_email"],
                "subject": f"✅ Ordem de Serviço aprovada — {o['numero']}",
                "html": f"""<div style="font-family:sans-serif;max-width:600px;margin:0 auto;padding:24px">
                  <h2 style="color:#059669">✅ Sua O.S foi aprovada!</h2>
                  <p>Olá, <strong>{o.get('colaborador_nome', o['colaborador_email'])}</strong>!</p>
                  <p>Sua Ordem de Serviço <strong>{o['numero']}</strong> foi aprovada pelo financeiro.</p>
                  <table style="width:100%;border-collapse:collapse;margin:20px 0">
                    <tr><td style="padding:8px;color:#888;font-size:12px">Destino</td><td style="padding:8px;font-size:13px">{municipio}</td></tr>
                    <tr style="background:#f9fafb"><td style="padding:8px;color:#888;font-size:12px">Data de ida</td><td style="padding:8px;font-size:13px">{o.get('data_ida','—')}</td></tr>
                    <tr><td style="padding:8px;color:#888;font-size:12px">Data de volta</td><td style="padding:8px;font-size:13px">{o.get('data_volta','—')}</td></tr>
                    <tr style="background:#f9fafb"><td style="padding:8px;color:#888;font-size:12px">Valor total</td><td style="padding:8px;font-size:13px;font-weight:600;color:#059669">R$ {float(o.get('valor_total') or 0):.2f}</td></tr>
                  </table>
                  <a href="https://voosuporte.com.br/colaborador/os" style="display:inline-block;background:#059669;color:#fff;padding:10px 20px;border-radius:8px;text-decoration:none;font-size:13px;font-weight:600;text-align:center">Visualizar no Portal →</a>
                </div>"""
            })
    except Exception as e:
        print(f"Erro e-mail aprovação O.S: {e}")
    return {"status": "aprovada"}

@app.post("/api/os/ordens/{id}/finalizar-prestacao")
async def finalizar_prestacao_os(id: str, request: Request):
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=401)
    try:
        supabase.table("os_ordens").update({"status": "prestacao_enviada"}).eq("id", id).execute()
        return {"status": "enviada"}
    except Exception as e:
        print(f"Erro ao finalizar prestacao: {e}")
        raise HTTPException(status_code=500, detail="Erro ao processar envio")

@app.post("/api/os/ordens/{id}/cancelar")
async def cancelar_os_ordem(id: str, request: Request):
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=401)
    supabase.table("os_ordens").update({"status": "cancelada"}).eq("id", id).execute()
    return {"status": "cancelada"}

@app.post("/api/os/ordens/{id}/reabrir")
async def reabrir_os_ordem(id: str, request: Request):
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=401)
    supabase.table("os_ordens").update({"status": "aprovada"}).eq("id", id).execute()
    return {"status": "reaberta"}

@app.post("/api/os/ordens/{id}/encerrar")
async def encerrar_os_ordem(id: str, request: Request):
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=401)
    user = supabase.auth.get_user(token)
    supabase.table("os_ordens").update({
        "status": "encerrada",
        "aprovado_por": user.user.email,
        "aprovado_em": datetime.now(timezone.utc).isoformat()
    }).eq("id", id).execute()
    return {"status": "encerrada"}

@app.delete("/api/os/ordens/{id}")
async def excluir_os_ordem(id: str, request: Request):
    token = request.cookies.get("token")
    role = request.cookies.get("role")
    if not token or role != "admin":
        raise HTTPException(status_code=403)
    # Só permite excluir O.S. que ainda não foram aprovadas/encerradas
    os_res = supabase.table("os_ordens").select("status").eq("id", id).execute()
    if not os_res.data:
        raise HTTPException(status_code=404)
    status_atual = os_res.data[0].get("status", "")
    if status_atual in ("aprovada", "encerrada", "prestacao_enviada", "prestacao_aprovada"):
        raise HTTPException(status_code=400, detail="Não é possível excluir uma O.S. aprovada ou encerrada.")
    # Remove dependências antes
    supabase.table("os_adiantamentos").delete().eq("os_id", id).execute()
    supabase.table("os_custos_empresa").delete().eq("os_id", id).execute()
    supabase.table("os_prestacao_contas").delete().eq("os_id", id).execute()
    supabase.table("os_ordens").delete().eq("id", id).execute()
    return {"status": "excluida"}

@app.get("/api/os/ordens/{id}/prestacao")
async def api_os_prestacao(id: str, request: Request):
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=401)
    resultado = supabase.table("os_prestacao_contas").select("*").eq("os_id", id).order("created_at").execute()
    return resultado.data

@app.post("/api/os/ordens/{id}/prestacao")
async def enviar_os_prestacao(id: str, request: Request, descricao: str = Form(...), tipo: str = Form(...), valor: float = Form(...), comprovante: UploadFile = File(None)):
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=401)
    user = supabase.auth.get_user(token)
    comprovante_url = await fazer_upload(comprovante) if comprovante and comprovante.filename else ""
    
    # Este comando APENAS insere o gasto. NÃO MUDA O STATUS DA O.S.
    supabase.table("os_prestacao_contas").insert({
        "os_id": id,
        "colaborador_email": user.user.email,
        "tipo": tipo,
        "descricao": descricao,
        "valor": valor,
        "comprovante_url": comprovante_url,
        "status": "pendente"
    }).execute()
    # Linha removida/comentada para não enviar automático ao salvar gasto:
    # supabase.table("os_ordens").update({"status": "prestacao_enviada"}).eq("id", id).execute()

    return {"status": "enviado"}

@app.post("/api/os/prestacao/{id}/aprovar")
async def aprovar_prestacao(id: str, request: Request):
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=401)
    user = supabase.auth.get_user(token)
    prestacao = supabase.table("os_prestacao_contas").select("*").eq("id", id).execute()
    if not prestacao.data:
        raise HTTPException(status_code=404)
    os_id = prestacao.data[0]["os_id"]
    supabase.table("os_prestacao_contas").update({
        "status": "aprovado",
        "aprovado_por": user.user.email,
        "aprovado_em": datetime.now(timezone.utc).isoformat()
    }).eq("id", id).execute()
    
    todas = supabase.table("os_prestacao_contas").select("status").eq("os_id", os_id).execute()
    nao_devolvidas = [p for p in todas.data if p["status"] != "devolvido"]
    if nao_devolvidas and all(p["status"] == "aprovado" for p in nao_devolvidas):
        supabase.table("os_ordens").update({"status": "prestacao_aprovada"}).eq("id", os_id).execute()
    
    try:
        prestacao = supabase.table("os_prestacao_contas").select("*").eq("id", id).execute()
        if prestacao.data:
            p = prestacao.data[0]
            os_data = supabase.table("os_ordens").select("numero").eq("id", p["os_id"]).execute()
            numero = os_data.data[0]["numero"] if os_data.data else "—"
            resend.Emails.send({
                "from": "Voo Suporte <noreply@voosuporte.com.br>",
                "to": p["colaborador_email"],
                "subject": f"✅ Prestação de contas aprovada — O.S {numero}",
                "html": f"""<div style="font-family:sans-serif;max-width:600px;margin:0 auto;padding:24px">
                  <h2 style="color:#059669">✅ Prestação aprovada!</h2>
                  <p>Sua prestação de contas da O.S <strong>{numero}</strong> foi aprovada pelo financeiro.</p>
                  <table style="width:100%;border-collapse:collapse;margin:16px 0">
                    <tr><td style="padding:8px;color:#888;font-size:12px">Tipo</td><td style="padding:8px;font-size:13px">{p['tipo']}</td></tr>
                    <tr style="background:#f9fafb"><td style="padding:8px;color:#888;font-size:12px">Descrição</td><td style="padding:8px;font-size:13px">{p['descricao']}</td></tr>
                    <tr><td style="padding:8px;color:#888;font-size:12px">Valor</td><td style="padding:8px;font-size:13px;font-weight:600;color:#059669">R$ {float(p['valor']):.2f}</td></tr>
                  </table>
                  <a href="https://voosuporte.com.br/colaborador/os" style="display:inline-block;background:#059669;color:#fff;padding:10px 20px;border-radius:8px;text-decoration:none;font-size:13px;font-weight:600">Ver minhas O.S →</a>
                </div>"""
            })
    except Exception as e:
        print(f"Erro e-mail aprovação prestação: {e}")
    return {"status": "aprovado"}

@app.post("/api/os/prestacao/{id}/devolver")
async def devolver_prestacao(id: str, request: Request, motivo: str = Form(...)):
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=401)
    prestacao = supabase.table("os_prestacao_contas").select("*").eq("id", id).execute()
    if not prestacao.data:
        raise HTTPException(status_code=404)
    p = prestacao.data[0]
    supabase.table("os_prestacao_contas").update({
        "status": "devolvido",
        "motivo_devolucao": motivo
    }).eq("id", id).execute()
    supabase.table("os_ordens").update({"status": "prestacao_devolvida"}).eq("id", p["os_id"]).execute()
    try:
        resend.Emails.send({
            "from": "Voo Suporte <noreply@voosuporte.com.br>",
            "to": p["colaborador_email"],
            "subject": f"⚠️ Prestação de contas devolvida",
            "html": f"""<div style="font-family:sans-serif;max-width:600px;margin:0 auto;padding:24px">
              <h2>Prestação de contas devolvida</h2>
              <p>Sua prestação de contas foi devolvida pelo financeiro.</p>
              <div style="background:#fef3c7;border:1px solid #fcd34d;border-radius:8px;padding:16px;margin:16px 0">
                <p style="color:#92400e;margin:0"><strong>Motivo:</strong> {motivo}</p>
              </div>
              <p style="color:#888;font-size:12px">Acesse o portal e corrija as informações.</p>
            </div>"""
        })
    except Exception as e:
        print(f"Erro e-mail devolução: {e}")
    return {"status": "devolvido"}

@app.get("/api/os/ordens/{id}/custos-empresa")
async def api_custos_empresa(id: str, request: Request):
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=401)
    resultado = supabase.table("os_custos_empresa").select("*").eq("os_id", id).order("created_at").execute()
    return resultado.data

@app.post("/api/os/ordens/{id}/custos-empresa")
async def criar_custo_empresa(id: str, request: Request, tipo: str = Form(...), descricao: str = Form(""), valor: float = Form(...), data_pagamento: str = Form("")):
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=401)
    user = supabase.auth.get_user(token)
    supabase.table("os_custos_empresa").insert({
        "os_id": id,
        "tipo": tipo,
        "descricao": descricao,
        "valor": valor,
        "data_pagamento": data_pagamento or None,
        "lancado_por": user.user.email
    }).execute()
    custos = supabase.table("os_custos_empresa").select("valor").eq("os_id", id).execute()
    total_empresa = sum(float(c["valor"]) for c in custos.data)
    supabase.table("os_ordens").update({"valor_total_empresa": total_empresa}).eq("id", id).execute()
    return {"status": "adicionado"}

@app.delete("/api/os/custos-empresa/{id}")
async def deletar_custo_empresa(id: str, request: Request):
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=401)
    custo = supabase.table("os_custos_empresa").select("os_id").eq("id", id).execute()
    supabase.table("os_custos_empresa").delete().eq("id", id).execute()
    if custo.data:
        os_id = custo.data[0]["os_id"]
        custos = supabase.table("os_custos_empresa").select("valor").eq("os_id", os_id).execute()
        total_empresa = sum(float(c["valor"]) for c in custos.data)
        supabase.table("os_ordens").update({"valor_total_empresa": total_empresa}).eq("id", os_id).execute()
    return {"status": "removido"}

@app.get("/api/financeiro/adiantamentos")
async def api_adiantamentos_avulsos(request: Request):
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=401)
    resultado = supabase.table("os_adiantamentos_avulsos").select("*").order("created_at", desc=True).execute()
    return resultado.data

@app.post("/api/financeiro/adiantamentos")
async def criar_adiantamento_avulso(request: Request, colaborador_email: str = Form(...), colaborador_nome: str = Form(...), tipo: str = Form(...), descricao: str = Form(""), valor: float = Form(...), data: str = Form("")):
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=401)
    user = supabase.auth.get_user(token)
    resultado = supabase.table("os_adiantamentos_avulsos").insert({
        "colaborador_email": colaborador_email,
        "colaborador_nome": colaborador_nome,
        "tipo": tipo,
        "descricao": descricao,
        "valor": valor,
        "data": data or datetime.now(timezone.utc).date().isoformat(),
        "lancado_por": user.user.email
    }).execute()
    return resultado.data[0]

@app.delete("/api/financeiro/adiantamentos/{id}")
async def deletar_adiantamento_avulso(id: str, request: Request):
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=401)
    supabase.table("os_adiantamentos_avulsos").delete().eq("id", id).execute()
    return {"status": "removido"}

@app.get("/api/financeiro/contas")
async def api_financeiro_contas(request: Request, tipo: str = None):
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=401)
    query = supabase.table("financeiro_contas").select("*,clientes(nome)").order("vencimento")
    if tipo:
        query = query.eq("tipo", tipo)
    resultado = query.execute()
    hoje = datetime.now(timezone.utc).date().isoformat()
    for c in resultado.data:
        if c["status"] == "pendente" and c["vencimento"] < hoje:
            supabase.table("financeiro_contas").update({"status": "vencido"}).eq("id", c["id"]).execute()
            c["status"] = "vencido"
    return resultado.data

@app.post("/api/financeiro/contas")
async def criar_financeiro_conta(request: Request, tipo: str = Form(...), descricao: str = Form(...), valor: float = Form(...), vencimento: str = Form(...), cliente_id: str = Form(""), observacoes: str = Form("")):
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=401)
    user = supabase.auth.get_user(token)
    resultado = supabase.table("financeiro_contas").insert({
        "tipo": tipo,
        "descricao": descricao,
        "valor": valor,
        "vencimento": vencimento,
        "cliente_id": cliente_id or None,
        "observacoes": observacoes,
        "lancado_por": user.user.email,
        "status": "pendente"
    }).execute()
    return resultado.data[0]

@app.post("/api/financeiro/contas/{id}/pagar")
async def pagar_financeiro_conta(id: str, request: Request, data_pagamento: str = Form("")):
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=401)
    supabase.table("financeiro_contas").update({
        "status": "pago",
        "data_pagamento": data_pagamento or datetime.now(timezone.utc).date().isoformat()
    }).eq("id", id).execute()
    return {"status": "pago"}

@app.delete("/api/financeiro/contas/{id}")
async def deletar_financeiro_conta(id: str, request: Request):
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=401)
    supabase.table("financeiro_contas").delete().eq("id", id).execute()
    return {"status": "removido"}

@app.get("/os/ordens/{id}/pdf")
async def gerar_pdf_os(id: str, request: Request):
    token = request.cookies.get("token")
    role = request.cookies.get("role")
    if not token:
        return RedirectResponse(url="/")
    try:
        from weasyprint import HTML
        
        user = supabase.auth.get_user(token)
        perfil = supabase.table("perfis").select("modulos").eq("id", str(user.user.id)).execute()
        modulos = perfil.data[0].get("modulos") or [] if perfil.data else []
        is_financeiro = role == "admin" or "financeiro" in modulos or "ordens_servico" in modulos

        os_data = supabase.table("os_ordens").select("*,os_departamentos(nome,valor_diaria,valor_meia_diaria),clientes(nome,estado,distancia_km)").eq("id", id).execute()
        if not os_data.data:
            raise HTTPException(status_code=404)
        o = os_data.data[0]

        custos_emp = supabase.table("os_custos_empresa").select("*").eq("os_id", id).execute()
        adiantamentos = o.get("adiantamentos") or []

        total_adiant = sum(float(a.get("valor", 0)) for a in adiantamentos)
        total_colab = float(o.get("valor_total") or 0) + total_adiant
        total_empresa = sum(float(c.get("valor", 0)) for c in custos_emp.data)
        investimento_total = total_colab + total_empresa
        
        def fmt(v): return f"R$ {float(v or 0):.2f}".replace(".", ",")
        def fmtdata(d): return d[8:10]+"/"+d[5:7]+"/"+d[0:4] if d else "—"

        adiant_rows = "".join(f"<tr><td>Adiantamento</td><td>{a.get('descricao', '')}</td><td style='text-align:right'>{fmt(a.get('valor', 0))}</td></tr>" for a in adiantamentos)
        custos_rows = ""
        if is_financeiro:
            custos_rows = "".join(f"<tr><td>Custo Empresa</td><td>{c.get('descricao', '')}</td><td style='text-align:right'>{fmt(c.get('valor', 0))}</td></tr>" for c in custos_emp.data)

        resumo_financeiro = f'<div class="total-card"><strong>Total OS: {fmt(investimento_total)}</strong></div>' if is_financeiro else f'<div class="total-card"><strong>A Receber: {fmt(total_colab)}</strong></div>'

        html_content = f"""<!DOCTYPE html>
        <html lang="pt-br"><head><meta charset="UTF-8">
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700&display=swap');
            @page {{ size: A4; margin: 1.5cm; }}
            body {{ font-family: 'Inter', sans-serif; color: #334155; font-size: 11px; }}
            .header {{ display: flex; justify-content: space-between; border-bottom: 2px solid #064e3b; padding-bottom: 10px; margin-bottom: 20px; }}
            h1 {{ font-size: 18px; color: #064e3b; margin: 0; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
            th {{ background: #f8fafc; text-align: left; padding: 8px; border-bottom: 1px solid #e2e8f0; }}
            td {{ padding: 8px; border-bottom: 1px solid #f1f5f9; }}
            .total-card {{ background: #0f172a; color: white; padding: 15px; border-radius: 8px; margin-top: 20px; text-align: right; }}
        </style></head><body>
            <div class="header">
                <div><h1>Voo Suporte</h1><p>O.S # {o['numero']}</p></div>
                <div style="text-align:right">Emitido em: {datetime.now().strftime('%d/%m/%Y')}</div>
            </div>
            <p><strong>Colaborador:</strong> {o['colaborador_nome']}<br>
            <strong>Município:</strong> {o.get('clientes', {}).get('nome', '—')}</p>
            <div style="background:#f1f5f9; padding: 10px; border-radius: 5px; margin: 10px 0;">
                <strong>Escopo:</strong><br>{o['servicos']}
            </div>
            <table>
                <thead><tr><th>Descrição</th><th style="text-align:right">Valor</th></tr></thead>
                <tbody>
                    <tr><td>Diárias ({o.get('total_dias')} dias)</td><td style="text-align:right">{fmt(o.get('valor_total_diarias'))}</td></tr>
                    {adiant_rows}
                    {custos_rows}
                </tbody>
            </table>
            {resumo_financeiro}
        </body></html>"""

        pdf_bytes = HTML(string=html_content).write_pdf()
        return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f"inline; filename=OS_{o['numero']}.pdf"})
    except Exception as e:
        print(f"Erro no PDF: {e}")
        raise HTTPException(status_code=500, detail="Erro ao gerar PDF")
