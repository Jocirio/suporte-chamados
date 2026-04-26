from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from supabase import create_client
from datetime import datetime, timedelta, timezone
import os
import resend
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

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
                    "from": "Inovatus Sistemas <noreply@voosuporte.com.br>",
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
            "from": "Inovatus Sistemas <noreply@voosuporte.com.br>",
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
              <a href="https://voosuporte.com.br/os/colaborador" style="display:inline-block;background:#059669;color:#fff;padding:10px 20px;border-radius:8px;text-decoration:none;font-size:13px;font-weight:600;margin-top:8px">Ver minhas O.S →</a>
            </div>"""
        })
    except Exception as e:
        print(f"Erro e-mail O.S colaborador: {e}")

# ===================== PÁGINAS =====================

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

@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    token = request.cookies.get("token")
    role = request.cookies.get("role")
    if not token or role != "admin":
        return RedirectResponse(url="/")
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
    if not token or role != "admin":
        return RedirectResponse(url="/")
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

@app.get("/financeiro", response_class=HTMLResponse)
async def financeiro_dashboard(request: Request):
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

# ===================== AUTH =====================

@app.post("/login")
async def login(email: str = Form(...), senha: str = Form(...)):
    try:
        res = supabase.auth.sign_in_with_password({"email": email, "password": senha})
        perfil = supabase.table("perfis").select("*").eq("id", str(res.user.id)).execute()
        
        role = perfil.data[0]["role"] if perfil.data else "colaborador"
        
        # Destino fixo para o portal novo
        destino = "/portal"
        
        response = RedirectResponse(url=destino, status_code=302)
        response.set_cookie("token", res.session.access_token, httponly=True)
        response.set_cookie("role", role, httponly=True)
        return response
    except Exception as e:
        print(f"Erro login: {e}")
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
            <div style="text-align:right;font-size:10px;color:#888">Inovatus Sistemas<br>Emitido em: {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M')}</div>
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
    
@app.post("/registrar")
async def registrar(email: str = Form(...), senha: str = Form(...), nome: str = Form(...)):
    try:
        res = supabase.auth.sign_up({"email": email, "password": senha})
        supabase.table("perfis").insert({"id": str(res.user.id), "email": email, "nome": nome, "role": "colaborador"}).execute()
        return RedirectResponse(url="/?cadastro=1", status_code=302)
    except:
        return RedirectResponse(url="/registrar?erro=1", status_code=302)

@app.get("/registrar", response_class=HTMLResponse)
async def registrar_page(request: Request):
    return templates.TemplateResponse(request=request, name="registrar.html")

# ===================== API USUÁRIOS =====================

@app.get("/api/meu-email")
async def meu_email(request: Request):
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=401)
    user = supabase.auth.get_user(token)
    perfil = supabase.table("perfis").select("*").eq("id", str(user.user.id)).execute()
    if perfil.data:
        p = perfil.data[0]
        return {
            "email": user.user.email,
            "nome": p.get("nome", ""),
            "role": p.get("role", "colaborador"),
            "modulos": p.get("modulos", ["chamados"])
        }
    return {"email": user.user.email, "nome": "", "role": "colaborador", "modulos": ["chamados"]}

@app.get("/api/usuarios")
async def api_usuarios(request: Request):
    token = request.cookies.get("token")
    role = request.cookies.get("role")
    if not token or role != "admin":
        raise HTTPException(status_code=403)
    resultado = supabase.table("perfis").select("*").order("nome").execute()
    return resultado.data

@app.post("/api/usuarios/{id}/perfil")
async def atualizar_perfil(id: str, request: Request, cargo: str = Form(""), departamento_id: str = Form(""), modulos: str = Form("[]")):
    token = request.cookies.get("token")
    role = request.cookies.get("role")
    if not token or role != "admin":
        raise HTTPException(status_code=403)
    import json
    modulos_list = json.loads(modulos)
    update_data = {"cargo": cargo, "modulos": modulos_list}
    if departamento_id:
        update_data["departamento_id"] = departamento_id
    else:
        update_data["departamento_id"] = None
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
    if not token or role != "admin":
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
                    "from": "Inovatus Sistemas <noreply@voosuporte.com.br>",
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

@app.post("/chamado")
async def criar_chamado(
    request: Request,
    colaborador_email: str = Form(...),
    unidade: str = Form(...),
    cliente_nome: str = Form(...),
    link_url: str = Form(""),
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
    evidencia_url = urls[0] if urls else ""
    resultado = supabase.table("chamados_controle").insert({
        "colaborador_email": colaborador_email,
        "unidade": unidade,
        "cliente_nome": cliente_nome,
        "link_url": link_url,
        "descricao_tecnica": descricao_tecnica,
        "evidencia_url": evidencia_url,
        "categoria": categoria,
        "prioridade": prioridade,
        "status": "aberto"
    }).execute()
    chamado_id = resultado.data[0]["id"]
    registrar_historico(chamado_id, "aberto", f"Chamado aberto por {colaborador_email}", colaborador_email)
    for i, url in enumerate(urls):
        supabase.table("chamados_mensagens").insert({
            "chamado_id": chamado_id,
            "autor_email": colaborador_email,
            "tipo": "abertura",
            "mensagem": descricao_tecnica if i == 0 else f"Anexo adicional {i+1}",
            "evidencia_url": url
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
            "from": "Inovatus Sistemas <noreply@voosuporte.com.br>",
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
                "from": "Inovatus Sistemas <noreply@voosuporte.com.br>",
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
async def api_os_ordens(request: Request):
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=401)
    user = supabase.auth.get_user(token)
    perfil = supabase.table("perfis").select("*").eq("id", str(user.user.id)).execute()
    if not perfil.data:
        raise HTTPException(status_code=403)
    p = perfil.data[0]
    modulos = p.get("modulos") or []
    apenas_meu = request.query_params.get("meu") == "1"
    if apenas_meu:
        resultado = supabase.table("os_ordens").select("*,os_departamentos(nome),clientes(nome,estado,distancia_km)").eq("colaborador_email", user.user.email).order("created_at", desc=True).execute()
    elif "financeiro" in modulos or "ordens_servico" in modulos or p.get("role") == "admin":
        resultado = supabase.table("os_ordens").select("*,os_departamentos(nome),clientes(nome,estado,distancia_km)").order("created_at", desc=True).execute()
    else:
        resultado = supabase.table("os_ordens").select("*,os_departamentos(nome),clientes(nome,estado,distancia_km)").eq("colaborador_email", user.user.email).order("created_at", desc=True).execute()
    return resultado.data

@app.post("/api/os/ordens")
async def criar_os_ordem(request: Request):
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=401)
    user = supabase.auth.get_user(token)
    body = await request.json()
    numero_res = await proximo_numero_os(request)
    numero = numero_res["numero"]
    resultado = supabase.table("os_ordens").insert({
        "numero": numero,
        "colaborador_email": body["colaborador_email"],
        "colaborador_nome": body["colaborador_nome"],
        "cargo": body["cargo"],
        "departamento_id": body["departamento_id"],
        "municipio_id": body["municipio_id"],
        "data_ida": body["data_ida"],
        "hora_ida": body["hora_ida"],
        "data_volta": body["data_volta"],
        "hora_volta": body["hora_volta"],
        "total_dias": body["total_dias"],
        "meio_transporte": body["meio_transporte"],
        "distancia_km": body["distancia_km"],
        "servicos": body["servicos"],
        "valor_diaria": body["valor_diaria"],
        "valor_total_diarias": body["valor_total_diarias"],
        "adiantamentos": body.get("adiantamentos", []),
        "valor_total": body["valor_total"],
        "status": "emitida",
        "criado_por": user.user.email,
        "observacoes": body.get("observacoes", "")
    }).execute()
    os_criada = resultado.data[0]
    enviar_email_os_colaborador(os_criada, body)
    return os_criada

@app.get("/api/os/ordens/{id}")
async def api_os_ordem(id: str, request: Request):
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=401)
    resultado = supabase.table("os_ordens").select("*,os_departamentos(nome,valor_diaria,valor_meia_diaria),clientes(nome,estado,distancia_km)").eq("id", id).execute()
    if not resultado.data:
        raise HTTPException(status_code=404)
    return resultado.data[0]

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
            resend.Emails.send({
                "from": "Inovatus Sistemas <noreply@voosuporte.com.br>",
                "to": o["colaborador_email"],
                "subject": f"✅ Ordem de Serviço aprovada — {o['numero']}",
                "html": f"""<div style="font-family:sans-serif;max-width:600px;margin:0 auto;padding:24px">
                  <h2 style="color:#059669">✅ Sua O.S foi aprovada!</h2>
                  <p>Olá, <strong>{o['colaborador_nome']}</strong>!</p>
                  <p>Sua Ordem de Serviço <strong>{o['numero']}</strong> foi aprovada pelo financeiro.</p>
                  <table style="width:100%;border-collapse:collapse;margin:20px 0">
                    <tr><td style="padding:8px;color:#888;font-size:12px">Destino</td><td style="padding:8px;font-size:13px">{o.get('clientes', {}).get('nome', '—') if o.get('clientes') else '—'}</td></tr>
                    <tr style="background:#f9fafb"><td style="padding:8px;color:#888;font-size:12px">Data de ida</td><td style="padding:8px;font-size:13px">{o['data_ida']}</td></tr>
                    <tr><td style="padding:8px;color:#888;font-size:12px">Data de volta</td><td style="padding:8px;font-size:13px">{o['data_volta']}</td></tr>
                    <tr style="background:#f9fafb"><td style="padding:8px;color:#888;font-size:12px">Valor total</td><td style="padding:8px;font-size:13px;font-weight:600;color:#059669">R$ {float(o['valor_total']):.2f}</td></tr>
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

# --- NOVAS ROTAS QUE VOCÊ DEVE INSERIR AQUI ---

@app.post("/api/os/ordens/{id}/finalizar-prestacao")
async def finalizar_prestacao_os(id: str, request: Request):
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=401)
    # Gatilho do botão roxo: muda o status da O.S. de uma vez só
    supabase.table("os_ordens").update({"status": "prestacao_enviada"}).eq("id", id).execute()
    return {"status": "enviada"}

@app.post("/api/os/ordens/{id}/reabrir")
async def reabrir_os_ordem(id: str, request: Request):
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=401)
    # Permite ao financeiro voltar o status para 'aprovada'
    supabase.table("os_ordens").update({"status": "aprovada"}).eq("id", id).execute()
    return {"status": "reaberta"}

# --- FIM DAS NOVAS ROTAS ---

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
                "from": "Inovatus Sistemas <noreply@voosuporte.com.br>",
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
            "from": "Inovatus Sistemas <noreply@voosuporte.com.br>",
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

@app.get("/api/financeiro/dashboard")
async def api_financeiro_dashboard(request: Request):
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=401)
    try:
        hoje = datetime.now(timezone.utc).date().isoformat()
        em7dias = (datetime.now(timezone.utc).date() + timedelta(days=7)).isoformat()
        ordens = supabase.table("os_ordens").select("*").execute()
        contas = supabase.table("financeiro_contas").select("*").execute()
        adiantamentos_avulsos = supabase.table("os_adiantamentos_avulsos").select("*").execute()
        custos_empresa = supabase.table("os_custos_empresa").select("*").execute()
        total_diarias = sum(float(o.get("valor_total_diarias") or 0) for o in ordens.data)
        total_adiant_os = sum(sum(float(a.get("valor", 0)) for a in (o.get("adiantamentos") or [])) for o in ordens.data)
        total_adiant_avulso = sum(float(a.get("valor") or 0) for a in adiantamentos_avulsos.data)
        total_custos_empresa = sum(float(c.get("valor") or 0) for c in custos_empresa.data)
        contas_pagar = [c for c in contas.data if c["tipo"] == "pagar"]
        contas_receber = [c for c in contas.data if c["tipo"] == "receber"]
        total_pagar = sum(float(c["valor"]) for c in contas_pagar if c["status"] != "pago")
        total_receber = sum(float(c["valor"]) for c in contas_receber if c["status"] != "pago")
        vencendo_pagar = len([c for c in contas_pagar if c["status"] == "pendente" and c["vencimento"] <= em7dias])
        vencendo_receber = len([c for c in contas_receber if c["status"] == "pendente" and c["vencimento"] <= em7dias])
        vencidas_pagar = len([c for c in contas_pagar if c["status"] == "vencido"])
        os_aguardando_aprovacao = len([o for o in ordens.data if o["status"] == "emitida"])
        prestacoes_pendentes = supabase.table("os_prestacao_contas").select("id").eq("status", "pendente").execute()
        colaboradores_dict = {}
        for o in ordens.data:
            email = o["colaborador_email"]
            if email not in colaboradores_dict: colaboradores_dict[email] = {"nome": o["colaborador_nome"], "adiantamentos": 0, "diarias": 0}
            colaboradores_dict[email]["diarias"] += float(o.get("valor_total_diarias") or 0)
            for a in (o.get("adiantamentos") or []): colaboradores_dict[email]["adiantamentos"] += float(a.get("valor", 0))
        for a in adiantamentos_avulsos.data:
            email = a["colaborador_email"]
            if email not in colaboradores_dict: colaboradores_dict[email] = {"nome": a["colaborador_nome"], "adiantamentos": 0, "diarias": 0}
            colaboradores_dict[email]["adiantamentos"] += float(a.get("valor") or 0)
        return {
            "total_diarias": total_diarias,
            "total_adiantamentos": total_adiant_os + total_adiant_avulso,
            "total_custos_empresa": total_custos_empresa,
            "total_pagar": total_pagar,
            "total_receber": total_receber,
            "vencendo_pagar": vencendo_pagar,
            "vencendo_receber": vencendo_receber,
            "vencidas_pagar": vencidas_pagar,
            "os_aguardando_aprovacao": os_aguardando_aprovacao,
            "prestacoes_pendentes": len(prestacoes_pendentes.data),
            "saldo_colaboradores": [{"email": k, "nome": v["nome"], "adiantamentos": v["adiantamentos"], "diarias": v["diarias"]} for k, v in colaboradores_dict.items()]
        }
    except Exception as e:
        print(f"Erro dashboard financeiro: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/os/ordens/{id}/pdf")
async def gerar_pdf_os(id: str, request: Request):
    token = request.cookies.get("token")
    role = request.cookies.get("role")
    if not token: return RedirectResponse(url="/")
    try:
        from weasyprint import HTML
        os_data = supabase.table("os_ordens").select("*,os_departamentos(nome,valor_diaria,valor_meia_diaria),clientes(nome,estado,distancia_km)").eq("id", id).execute()
        if not os_data.data: raise HTTPException(status_code=404)
        o = os_data.data[0]
        
        custos_emp = supabase.table("os_custos_empresa").select("*").eq("os_id", id).execute()
        adiantamentos = o.get("adiantamentos") or []
        
        # === CORREÇÃO AQUI: Extraímos os dados antes do HTML ===
        total_adiant = sum(float(a.get('valor', 0)) for a in adiantamentos)
        total_colab = float(o.get('valor_total') or 0) + total_adiant
        total_empresa = sum(float(c.get('valor', 0)) for c in custos_emp.data)
        investimento_total = total_colab + total_empresa
        
        # Extraímos o nome do cliente de forma segura para não usar dicionário na f-string
        cliente_obj = o.get('clientes') or {}
        municipio_nome = str(cliente_obj.get('nome', '—'))
        # ======================================================

        def fmt(v): return f"R$ {float(v or 0):.2f}".replace(".", ",")
        def fmtdata(d):
            if not d: return "—"
            parts = str(d)[:10].split("-")
            return f"{parts[2]}/{parts[1]}/{parts[0]}"

        adiant_rows = "".join([f"<tr><td>Adiantamento</td><td>{a.get('descricao','')} ({a.get('tipo','')})</td><td style='text-align:right'>{fmt(a.get('valor',0))}</td></tr>" for a in adiantamentos])
        
        custos_rows = ""
        if role == "admin":
            custos_rows = "".join([f"<tr><td>Custo Empresa</td><td>{c.get('descricao','')} ({c.get('tipo','')})</td><td style='text-align:right'>{fmt(c.get('valor',0))}</td></tr>" for c in custos_emp.data])

        if role == "admin":
            resumo_financeiro = f"""
                <div class="total-row"><span>(+) Diárias e Adiantamentos</span><span>{fmt(total_colab)}</span></div>
                <div class="total-row"><span>(+) Custos Diretos Inovatus</span><span>{fmt(total_empresa)}</span></div>
                <div class="total-row main">
                    <div>
                        <span style="font-size: 10px; text-transform: uppercase; color: #94a3b8;">Investimento Total na O.S</span><br>
                        <strong>{fmt(investimento_total)}</strong>
                    </div>
                </div>"""
        else:
            resumo_financeiro = f"""
                <div class="total-row main">
                    <div>
                        <span style="font-size: 10px; text-transform: uppercase; color: #94a3b8;">Total a Receber</span><br>
                        <strong>{fmt(total_colab)}</strong>
                    </div>
                </div>"""

        html_content = f"""<!DOCTYPE html>
        <html lang="pt-br"><head><meta charset="UTF-8">
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
            @page {{ size: A4; margin: 0; }}
            body {{ font-family: 'Inter', sans-serif; color: #334155; margin: 0; padding: 0; background: #fff; }}
            .sidebar-accent {{ position: absolute; left: 0; top: 0; bottom: 0; width: 8px; background: #064e3b; }}
            .container {{ padding: 40px 50px; }}
            .header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 40px; }}
            .logo-placeholder {{ width: 60px; height: 60px; background: #064e3b; border-radius: 12px; display: flex; align-items: center; justify-content: center; overflow: hidden; }}
            .company-data h1 {{ margin: 0; font-size: 22px; color: #0f172a; letter-spacing: -0.5px; }}
            .company-data p {{ margin: 2px 0 0; font-size: 10px; color: #64748b; text-transform: uppercase; }}
            .os-badge {{ text-align: right; }}
            .os-number {{ font-size: 28px; font-weight: 800; color: #064e3b; margin: 0; }}
            .os-date {{ font-size: 11px; color: #94a3b8; }}
            .status-banner {{ background: #f8fafc; border: 1px solid #e2e8f0; padding: 15px; border-radius: 12px; display: flex; justify-content: space-between; margin-bottom: 30px; }}
            .status-info span {{ display: block; font-size: 9px; text-transform: uppercase; color: #94a3b8; font-weight: 700; margin-bottom: 3px; }}
            .status-info strong {{ font-size: 13px; color: #1e293b; }}
            .section {{ margin-bottom: 25px; }}
            .section-title {{ font-size: 11px; font-weight: 800; text-transform: uppercase; color: #064e3b; letter-spacing: 1px; margin-bottom: 12px; }}
            .escopo-box {{ background: #f1f5f9; border: 1px solid #e2e8f0; padding: 20px; border-radius: 8px; line-height: 1.6; font-size: 12px; color: #1e293b; }}
            .finance-table-container {{ border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden; }}
            table {{ width: 100%; border-collapse: collapse; }}
            th {{ text-align: left; padding: 12px 10px; background: #f8fafc; color: #475569; font-size: 10px; text-transform: uppercase; font-weight: 700; border-bottom: 1px solid #e2e8f0; }}
            td {{ padding: 12px 10px; border-bottom: 1px solid #f1f5f9; font-size: 11px; }}
            .financial-summary {{ margin-top: 30px; display: flex; justify-content: flex-end; }}
            .total-card {{ background: #0f172a; color: white; padding: 25px; border-radius: 16px; width: 320px; }}
            .total-row {{ display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 11px; opacity: 0.8; }}
            .total-row.main {{ margin-top: 15px; padding-top: 15px; border-top: 1px solid #334155; opacity: 1; }}
            .total-row.main strong {{ font-size: 22px; color: #10b981; }}
            .signature-section {{ margin-top: 60px; display: flex; justify-content: space-between; gap: 40px; }}
            .sig-box {{ text-align: center; width: 45%; }}
            .sig-line {{ border-top: 1px solid #e2e8f0; margin-bottom: 8px; padding-top: 5px; }}
            .sig-box span {{ font-size: 10px; color: #64748b; font-weight: 600; }}
        </style></head><body>
            <div class="sidebar-accent"></div>
            <div class="container">
                <div class="header">
                    <div class="logo-box">
                        <div class="logo-placeholder"><img src="https://voosuporte.com.br/static/logo.png" style="max-width:100%; max-height:100%;"></div>
                        <div class="company-data"><h1>Inovatus Sistemas</h1><p>Tecnologia e Gestão em Saúde</p></div>
                    </div>
                    <div class="os-badge">
                        <p class="os-date">EMITIDO EM {fmtdata(str(o['created_at'])[:10])}</p>
                        <h2 class="os-number">O.S #{o['numero']}</h2>
                    </div>
                </div>
                <div class="status-banner">
                    <div class="status-info"><span>Colaborador</span><strong>{o['colaborador_nome']}</strong></div>
                    <div class="status-info"><span>Município</span><strong>{municipio_nome}</strong></div>
                    <div class="status-info"><span>Status</span><strong style="color: #059669;">● {o['status'].upper()}</strong></div>
                </div>
                <div class="section">
                    <div class="section-title">Escopo dos Serviços</div>
                    <div class="escopo-box">{o['servicos']}</div>
                </div>
                <div class="section">
                    <div class="section-title">Detalhamento Financeiro</div>
                    <div class="finance-table-container">
                        <table>
                            <thead><tr><th>Categoria</th><th>Descrição</th><th style="text-align:right">Valor</th></tr></thead>
                            <tbody>
                                <tr><td>Diárias</td><td>Total de diárias para o período</td><td style="text-align:right">{fmt(o.get('valor_total_diarias', 0))}</td></tr>
                                {adiant_rows}
                                {custos_rows}
                            </tbody>
                        </table>
                    </div>
                </div>
                <div class="financial-summary"><div class="total-card">{resumo_financeiro}</div></div>
                <div class="signature-section">
                    <div class="sig-box"><div class="sig-line"></div><span>{o['colaborador_nome']}</span><br><small>Assinatura do Colaborador</small></div>
                    <div class="sig-box"><div class="sig-line"></div><span>Diretor Financeiro</span><br><small>Inovatus Sistemas</small></div>
                </div>
            </div>
        </body></html>"""
        
        pdf_bytes = HTML(string=html_content).write_pdf()
        nome_os = f"OS_{str(o['numero']).replace('/', '-')}.pdf"
        
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"inline; filename={nome_os}"}
        )
    except Exception as e:
        print(f"Erro detalhado no PDF: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao processar PDF: {str(e)}")
