from fastapi import FastAPI, UploadFile, File, Form, HTTPException
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
    supabase.storage.from_("evidencias").upload(nome, conteudo)
    return supabase.storage.from_("evidencias").get_public_url(nome)

def notificar_admins(assunto: str, html: str):
    try:
        admins = supabase.table("perfis").select("email").eq("role", "admin").eq("ativo", True).execute()
        for admin in admins.data:
            try:
                resend.Emails.send({
                    "from": "Suporte Técnico <onboarding@resend.dev>",
                    "to": admin["email"],
                    "subject": assunto,
                    "html": html
                })
            except Exception as e:
                print(f"Erro e-mail admin {admin['email']}: {e}")
    except Exception as e:
        print(f"Erro ao buscar admins: {e}")

@app.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="login.html")

@app.get("/portal", response_class=HTMLResponse)
async def portal(request: Request):
    token = request.cookies.get("token")
    if not token:
        return RedirectResponse(url="/")
    return templates.TemplateResponse(request=request, name="portal.html")

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
@app.post("/login")
async def login(email: str = Form(...), senha: str = Form(...)):
    try:
        res = supabase.auth.sign_in_with_password({"email": email, "password": senha})
        perfil = supabase.table("perfis").select("*").eq("id", str(res.user.id)).execute()
        role = perfil.data[0]["role"] if perfil.data else "colaborador"
        modulos = perfil.data[0].get("modulos") or ["chamados"] if perfil.data else ["chamados"]
        tem_os = "ordens_servico" in modulos or "financeiro" in modulos
        if tem_os:
            destino = "/portal"
        elif role == "admin":
            destino = "/admin"
        else:
            destino = "/meus-chamados"
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
                    "from": "Suporte Técnico <onboarding@resend.dev>",
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
        html = f"""
        <div style="font-family:sans-serif;max-width:600px;margin:0 auto;padding:24px">
          <h2 style="color:#6366f1">📊 Relatório Semanal — Suporte Técnico</h2>
          <p style="color:#888">Semana encerrada em {datetime.utcnow().strftime('%d/%m/%Y')}</p>
          <table style="width:100%;border-collapse:collapse;margin:20px 0">
            <tr style="background:#f9fafb"><td style="padding:12px;border:1px solid #e5e7eb;font-weight:600">Total de chamados</td><td style="padding:12px;border:1px solid #e5e7eb;text-align:center;font-size:18px;font-weight:700">{total}</td></tr>
            <tr><td style="padding:12px;border:1px solid #e5e7eb">🆕 Abertos / sem Qualitor</td><td style="padding:12px;border:1px solid #e5e7eb;text-align:center;color:#6366f1;font-weight:600">{abertos}</td></tr>
            <tr style="background:#f9fafb"><td style="padding:12px;border:1px solid #e5e7eb">✅ Respondidos pelo parceiro</td><td style="padding:12px;border:1px solid #e5e7eb;text-align:center;color:#d97706;font-weight:600">{pendentes}</td></tr>
            <tr><td style="padding:12px;border:1px solid #e5e7eb">✔ Encerrados</td><td style="padding:12px;border:1px solid #e5e7eb;text-align:center;color:#059669;font-weight:600">{fechados}</td></tr>
            <tr style="background:#fef2f2"><td style="padding:12px;border:1px solid #e5e7eb">⚠️ SLA vencido</td><td style="padding:12px;border:1px solid #e5e7eb;text-align:center;color:#dc2626;font-weight:600">{sla_vencidos}</td></tr>
          </table>
          <p style="color:#888;font-size:12px">Acesse o sistema para mais detalhes.</p>
        </div>
        """
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
        html = f"""
        <div style="font-family:sans-serif;max-width:600px;margin:0 auto;padding:24px">
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
        </div>
        """
        notificar_admins("📊 Relatório Semanal — Suporte Técnico", html)
        return {"status": "enviado"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
            "from": "Suporte Técnico <onboarding@resend.dev>",
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
                "from": "Suporte Técnico <onboarding@resend.dev>",
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
# ===================== MÓDULO O.S =====================

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
@app.get("/os/colaborador", response_class=HTMLResponse)
async def os_colaborador(request: Request):
    token = request.cookies.get("token")
    if not token:
        return RedirectResponse(url="/")
    return templates.TemplateResponse(request=request, name="os_colaborador.html")
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

# API — Departamentos
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

# API — Municípios
# API — Municípios (unificado com clientes)
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

# API — Gerar número da O.S
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

# API — Ordens de Serviço
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
    if "financeiro" in modulos or "ordens_servico" in modulos:
        resultado = supabase.table("os_ordens").select("*,os_departamentos(nome),clientes(nome,estado,distancia_km)").order("created_at", desc=True).execute()
    else:
        resultado = supabase.table("os_ordens").select("*,os_departamentos(nome),os_municipios(nome,estado)").eq("colaborador_email", user.user.email).order("created_at", desc=True).execute()
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
    return resultado.data[0]

@app.get("/api/os/ordens/{id}")
async def api_os_ordem(id: str, request: Request):
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=401)
    resultado = supabase.table("os_ordens").select("*,os_departamentos(nome,valor_diaria,valor_meia_diaria),os_municipios(nome,estado,distancia_km)").eq("id", id).execute()
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
    return {"status": "aprovada"}

@app.post("/api/os/ordens/{id}/cancelar")
async def cancelar_os_ordem(id: str, request: Request):
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=401)
    supabase.table("os_ordens").update({"status": "cancelada"}).eq("id", id).execute()
    return {"status": "cancelada"}

# API — Prestação de Contas
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
    supabase.table("os_prestacao_contas").insert({
        "os_id": id,
        "colaborador_email": user.user.email,
        "tipo": tipo,
        "descricao": descricao,
        "valor": valor,
        "comprovante_url": comprovante_url,
        "status": "pendente"
    }).execute()
    supabase.table("os_ordens").update({"status": "prestacao_enviada"}).eq("id", id).execute()
    return {"status": "enviado"}

@app.post("/api/os/prestacao/{id}/aprovar")
async def aprovar_prestacao(id: str, request: Request):
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=401)
    user = supabase.auth.get_user(token)
    supabase.table("os_prestacao_contas").update({
        "status": "aprovado",
        "aprovado_por": user.user.email,
        "aprovado_em": datetime.now(timezone.utc).isoformat()
    }).eq("id", id).execute()
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
            "from": "Suporte Técnico <onboarding@resend.dev>",
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

@app.get("/api/os/colaboradores")
async def api_os_colaboradores(request: Request):
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=401)
    resultado = supabase.table("perfis").select("*").eq("ativo", True).order("nome").execute()
    return resultado.data
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

@app.get("/os/ordens/{id}/pdf")
async def gerar_pdf_os(id: str, request: Request):
    token = request.cookies.get("token")
    if not token:
        return RedirectResponse(url="/")
    try:
        from weasyprint import HTML
        import base64
        os_data = supabase.table("os_ordens").select("*,os_departamentos(nome,valor_diaria,valor_meia_diaria),os_municipios(nome,estado,distancia_km)").eq("id", id).execute()
        if not os_data.data:
            raise HTTPException(status_code=404)
        o = os_data.data[0]
        adiantamentos = o.get("adiantamentos") or []
        total_adiant = sum(float(a.get("valor", 0)) for a in adiantamentos)
        def fmt(v): return f"R$ {float(v or 0):.2f}".replace(".", ",")
        def fmtdata(d): 
            if not d: return "—"
            from datetime import date
            parts = d.split("-")
            return f"{parts[2]}/{parts[1]}/{parts[0]}"
        adiant_rows = ""
        for a in adiantamentos:
            adiant_rows += f"""
            <tr>
                <td>{a.get('tipo','')}</td>
                <td>{a.get('descricao','')}</td>
                <td>{a.get('forma','Dinheiro')}</td>
                <td style="text-align:right">{fmt(a.get('valor',0))}</td>
            </tr>"""
        if not adiant_rows:
            adiant_rows = '<tr><td colspan="4" style="color:#888;font-style:italic">Nenhum adiantamento</td></tr>'
        html_content = f"""
<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="UTF-8">
<style>
  @page {{ size: A4; margin: 2cm; }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: Arial, sans-serif; font-size: 12px; color: #111; line-height: 1.5; }}
  .header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 3px solid #059669; padding-bottom: 16px; margin-bottom: 20px; }}
  .logo-area {{ display: flex; align-items: center; gap: 12px; }}
  .logo-text {{ font-size: 22px; font-weight: 700; color: #059669; }}
  .logo-sub {{ font-size: 11px; color: #666; }}
  .os-numero {{ text-align: right; }}
  .os-numero-label {{ font-size: 11px; color: #666; text-transform: uppercase; letter-spacing: 1px; }}
  .os-numero-val {{ font-size: 28px; font-weight: 700; color: #059669; font-family: monospace; }}
  .os-data {{ font-size: 11px; color: #666; margin-top: 4px; }}
  .section {{ margin-bottom: 18px; }}
  .section-title {{ font-size: 10px; font-weight: 700; color: #059669; text-transform: uppercase; letter-spacing: 1px; border-bottom: 1px solid #e5e7eb; padding-bottom: 4px; margin-bottom: 10px; }}
  .grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }}
  .grid-3 {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; }}
  .field {{ display: flex; flex-direction: column; gap: 2px; }}
  .field-label {{ font-size: 10px; color: #666; text-transform: uppercase; letter-spacing: 0.5px; }}
  .field-value {{ font-size: 12px; font-weight: 600; color: #111; }}
  .servicos-box {{ background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 6px; padding: 10px 12px; font-size: 12px; line-height: 1.7; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 11px; }}
  th {{ background: #f0fdf4; color: #059669; font-weight: 700; text-transform: uppercase; font-size: 10px; letter-spacing: 0.5px; padding: 8px 10px; text-align: left; border-bottom: 2px solid #059669; }}
  td {{ padding: 8px 10px; border-bottom: 1px solid #e5e7eb; }}
  tr:last-child td {{ border-bottom: none; }}
  .total-box {{ background: #f0fdf4; border: 2px solid #059669; border-radius: 8px; padding: 14px 18px; display: flex; justify-content: space-between; align-items: center; margin-top: 18px; }}
  .total-label {{ font-size: 13px; font-weight: 700; color: #166534; }}
  .total-val {{ font-size: 22px; font-weight: 700; color: #059669; font-family: monospace; }}
  .assinaturas {{ display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 16px; margin-top: 40px; }}
  .assinatura {{ text-align: center; }}
  .assinatura-linha {{ border-top: 1px solid #111; padding-top: 6px; margin-top: 40px; }}
  .assinatura-nome {{ font-size: 11px; font-weight: 700; }}
  .assinatura-cargo {{ font-size: 10px; color: #666; }}
  .footer {{ margin-top: 30px; padding-top: 10px; border-top: 1px solid #e5e7eb; font-size: 10px; color: #888; text-align: center; }}
  .badge {{ display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: 10px; font-weight: 700; text-transform: uppercase; }}
  .badge-emitida {{ background: #dbeafe; color: #1d4ed8; }}
  .badge-aprovada {{ background: #dcfce7; color: #166534; }}
</style>
</head>
<body>
  <div class="header">
    <div class="logo-area">
      <div>
        <div class="logo-text">Inovatus</div>
        <div class="logo-sub">Sistemas de Informática Ltda</div>
      </div>
    </div>
    <div class="os-numero">
      <div class="os-numero-label">Ordem de Serviço</div>
      <div class="os-numero-val">Nº {o['numero']}</div>
      <div class="os-data">Emitida em {fmtdata(str(o['created_at'])[:10])}</div>
    </div>
  </div>

  <div class="section">
    <div class="section-title">Colaborador</div>
    <div class="grid-2">
      <div class="field"><div class="field-label">Nome</div><div class="field-value">{o['colaborador_nome']}</div></div>
      <div class="field"><div class="field-label">Cargo / Função</div><div class="field-value">{o['cargo']}</div></div>
      <div class="field"><div class="field-label">Departamento</div><div class="field-value">{o.get('os_departamentos', {}).get('nome', '—') if o.get('os_departamentos') else '—'}</div></div>
      <div class="field"><div class="field-label">E-mail</div><div class="field-value">{o['colaborador_email']}</div></div>
    </div>
  </div>

  <div class="section">
    <div class="section-title">Destino e período</div>
    <div class="grid-3">
      <div class="field"><div class="field-label">Município</div><div class="field-value">{o.get('os_municipios', {}).get('nome', '—') if o.get('os_municipios') else '—'} — {o.get('os_municipios', {}).get('estado', '') if o.get('os_municipios') else ''}</div></div>
      <div class="field"><div class="field-label">Data de ida</div><div class="field-value">{fmtdata(o['data_ida'])} às {o['hora_ida'][:5]}</div></div>
      <div class="field"><div class="field-label">Data de volta</div><div class="field-value">{fmtdata(o['data_volta'])} às {o['hora_volta'][:5]}</div></div>
      <div class="field"><div class="field-label">Total de dias</div><div class="field-value">{o['total_dias']} dia{'s' if float(o['total_dias']) != 1 else ''}</div></div>
      <div class="field"><div class="field-label">Meio de transporte</div><div class="field-value">{o['meio_transporte']}</div></div>
      <div class="field"><div class="field-label">Distância total</div><div class="field-value">{float(o['distancia_km']) * 2:.0f} km (ida + volta)</div></div>
    </div>
  </div>

  <div class="section">
    <div class="section-title">Serviços a executar</div>
    <div class="servicos-box">{o['servicos']}</div>
    {f'<div style="margin-top:8px;font-size:11px;color:#666"><strong>Obs:</strong> {o["observacoes"]}</div>' if o.get('observacoes') else ''}
  </div>

  <div class="section">
    <div class="section-title">Valores e adiantamentos</div>
    <table>
      <thead>
        <tr>
          <th>Descrição</th>
          <th>Detalhes</th>
          <th>Forma</th>
          <th style="text-align:right">Valor</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><strong>Diárias</strong></td>
          <td>{o['total_dias']} dia{'s' if float(o['total_dias']) != 1 else ''} × {fmt(o['valor_diaria'])}</td>
          <td>—</td>
          <td style="text-align:right"><strong>{fmt(o['valor_total_diarias'])}</strong></td>
        </tr>
        {adiant_rows}
      </tbody>
    </table>
    <div class="total-box">
      <div class="total-label">Valor total da O.S</div>
      <div class="total-val">{fmt(o['valor_total'])}</div>
    </div>
  </div>

  <div class="section">
    <div class="section-title">Assinaturas</div>
    <div class="assinaturas">
      <div class="assinatura">
        <div class="assinatura-linha"></div>
        <div class="assinatura-nome">Edvaldo Marques da Silva</div>
        <div class="assinatura-cargo">Diretor Técnico</div>
      </div>
      <div class="assinatura">
        <div class="assinatura-linha"></div>
        <div class="assinatura-nome">Jocirio Lara</div>
        <div class="assinatura-cargo">Coordenador Saúde</div>
      </div>
      <div class="assinatura">
        <div class="assinatura-linha"></div>
        <div class="assinatura-nome">Bianca Marques</div>
        <div class="assinatura-cargo">Financeiro</div>
      </div>
      <div class="assinatura">
        <div class="assinatura-linha"></div>
        <div class="assinatura-nome">{o['colaborador_nome']}</div>
        <div class="assinatura-cargo">Executor</div>
      </div>
    </div>
  </div>

  <div class="footer">
    Inovatus Sistemas de Informática Ltda · O.S Nº {o['numero']} · Gerado em {datetime.now(timezone.utc).strftime('%d/%m/%Y às %H:%M')} UTC
  </div>
</body>
</html>"""
        from weasyprint import HTML
        from fastapi.responses import Response
        pdf_bytes = HTML(string=html_content).write_pdf()
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"inline; filename=OS_{o['numero'].replace('/', '-')}.pdf"}
        )
    except Exception as e:
        print(f"Erro PDF: {e}")
        raise HTTPException(status_code=500, detail=str(e))
        # API — Tipos de transporte
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

# API — Tipos de adiantamento
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

# API — Configurar numeração
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

# API — Ver próximo número
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
