from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from supabase import create_client
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

@app.post("/login")
async def login(email: str = Form(...), senha: str = Form(...)):
    try:
        res = supabase.auth.sign_in_with_password({"email": email, "password": senha})
        perfil = supabase.table("perfis").select("role").eq("id", str(res.user.id)).execute()
        role = perfil.data[0]["role"] if perfil.data else "colaborador"
        response = RedirectResponse(url="/admin" if role == "admin" else "/meus-chamados", status_code=302)
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
    return {"email": user.user.email}

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
    arquivo: UploadFile = File(None)
):
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=401)
    if not arquivo or not arquivo.filename:
        raise HTTPException(status_code=400, detail="Anexo obrigatório")
    evidencia_url = await fazer_upload(arquivo)
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
    supabase.table("chamados_mensagens").insert({
        "chamado_id": chamado_id,
        "autor_email": colaborador_email,
        "tipo": "abertura",
        "mensagem": descricao_tecnica,
        "evidencia_url": evidencia_url
    }).execute()
    prioridade_label = {"baixa": "🟢 Baixa", "media": "🟡 Média", "alta": "🔴 Alta", "urgente": "🚨 Urgente"}.get(prioridade, prioridade)
    categoria_label = {"erro_sistema": "Erro de sistema", "acesso": "Acesso", "lentidao": "Lentidão", "duvida": "Dúvida", "implantacao": "Implantação", "outro": "Outro"}.get(categoria, categoria)
    notificar_admins(
        f"🆕 Novo chamado — {unidade} [{prioridade_label}]",
        f"""<div style="font-family:sans-serif;max-width:600px;margin:0 auto;padding:24px">
          <h2>Novo chamado aberto</h2>
          <table style="width:100%;border-collapse:collapse;margin-bottom:16px">
            <tr><td style="padding:6px 0;color:#888;font-size:12px;width:120px">Colaborador</td><td style="font-size:13px">{colaborador_email}</td></tr>
            <tr><td style="padding:6px 0;color:#888;font-size:12px">Unidade</td><td style="font-size:13px">{unidade}</td></tr>
            <tr><td style="padding:6px 0;color:#888;font-size:12px">Cliente</td><td style="font-size:13px">{cliente_nome}</td></tr>
            <tr><td style="padding:6px 0;color:#888;font-size:12px">Categoria</td><td style="font-size:13px">{categoria_label}</td></tr>
            <tr><td style="padding:6px 0;color:#888;font-size:12px">Prioridade</td><td style="font-size:13px">{prioridade_label}</td></tr>
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
    supabase.table("chamados_controle").update({"unidade": unidade, "cliente_nome": cliente_nome, "descricao_tecnica": descricao_tecnica}).eq("id", id).execute()
    registrar_historico(id, "editado", "Chamado editado pelo admin", user.user.email)
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
