from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from supabase import create_client
import anthropic
import os
import resend
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
resend.api_key = os.getenv("RESEND_KEY")
claude = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_KEY"))

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
    except:
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
        resultado = supabase.table("chamados_controle").select("*").eq("colaborador_email", email).order("created_at", desc=True).execute()
        return resultado.data
    except:
        raise HTTPException(status_code=401)

@app.get("/api/chamados")
async def api_chamados(request: Request):
    token = request.cookies.get("token")
    role = request.cookies.get("role")
    if not token or role != "admin":
        raise HTTPException(status_code=403)
    resultado = supabase.table("chamados_controle").select("*").order("created_at", desc=True).execute()
    return resultado.data

@app.post("/api/melhorar-texto")
async def melhorar_texto(request: Request, texto: str = Form(...)):
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=401)
    try:
        message = claude.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            system="Você é um assistente especializado em suporte técnico de sistemas de saúde pública. Reescreva a descrição do problema de forma técnica, clara e objetiva: 'Ao tentar [ação], na tela [local], o sistema deveria [comportamento esperado], porém [comportamento real].' Máximo 3 frases. Responda APENAS com o texto reescrito.",
            messages=[{"role": "user", "content": f"Reescreva: \"{texto}\""}]
        )
        return {"texto": message.content[0].text.strip()}
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
    arquivo: UploadFile = File(None)
):
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=401)

    evidencia_url = ""
    if arquivo and arquivo.filename:
        conteudo = await arquivo.read()
        nome = f"{os.urandom(8).hex()}_{arquivo.filename}"
        supabase.storage.from_("evidencias").upload(nome, conteudo)
        evidencia_url = supabase.storage.from_("evidencias").get_public_url(nome)

    resultado = supabase.table("chamados_controle").insert({
        "colaborador_email": colaborador_email,
        "unidade": unidade,
        "cliente_nome": cliente_nome,
        "link_url": link_url,
        "descricao_tecnica": descricao_tecnica,
        "evidencia_url": evidencia_url,
        "status": "aberto"
    }).execute()

    return JSONResponse({"id": resultado.data[0]["id"], "status": "registrado"})

@app.post("/chamado/{id}/qualitor")
async def vincular_qualitor(id: str, request: Request, qualitor_id: str = Form(...)):
    token = request.cookies.get("token")
    role = request.cookies.get("role")
    if not token or role != "admin":
        raise HTTPException(status_code=403)
    supabase.table("chamados_controle").update({"qualitor_id": qualitor_id}).eq("id", id).execute()
    return {"status": "vinculado"}

@app.post("/chamado/{id}/resposta")
async def salvar_resposta(id: str, request: Request, resposta: str = Form(...)):
    token = request.cookies.get("token")
    role = request.cookies.get("role")
    if not token or role != "admin":
        raise HTTPException(status_code=403)

    chamado = supabase.table("chamados_controle").select("*").eq("id", id).execute()
    if not chamado.data:
        raise HTTPException(status_code=404)

    c = chamado.data[0]

    supabase.table("chamados_controle").update({
        "resposta_parceiro": resposta,
        "status": "pendente_dev",
        "ultima_interacao": "now()"
    }).eq("id", id).execute()

    try:
        resend.Emails.send({
            "from": "Suporte Técnico <onboarding@resend.dev>",
            "to": c["colaborador_email"],
            "subject": f"Resposta do parceiro — Chamado {id[:8].upper()}",
            "html": f"""
            <div style="font-family:sans-serif;max-width:600px;margin:0 auto;padding:24px">
              <h2 style="color:#1a1a18;margin-bottom:8px">Resposta recebida no seu chamado</h2>
              <p style="color:#555;font-size:14px;margin-bottom:16px">
                O parceiro Qualitor respondeu ao seu chamado <strong>{id[:8].upper()}</strong> — {c['cliente_nome']}.
              </p>
              <div style="background:#f0faf5;border:1px solid #a8dfc3;border-radius:8px;padding:16px;margin-bottom:16px">
                <p style="font-size:13px;color:#1a1a18;line-height:1.6;margin:0">{resposta}</p>
              </div>
              <p style="color:#888;font-size:12px">
                Acesse o sistema para ver todos os detalhes e tomar as ações necessárias.
              </p>
            </div>
            """
        })
    except Exception as e:
        print(f"Erro ao enviar e-mail: {e}")

    return {"status": "salvo"}

@app.post("/registrar")
async def registrar(email: str = Form(...), senha: str = Form(...), nome: str = Form(...)):
    try:
        res = supabase.auth.sign_up({"email": email, "password": senha})
        supabase.table("perfis").insert({
            "id": str(res.user.id),
            "email": email,
            "nome": nome,
            "role": "colaborador"
        }).execute()
        return RedirectResponse(url="/?cadastro=1", status_code=302)
    except:
        return RedirectResponse(url="/registrar?erro=1", status_code=302)

@app.get("/registrar", response_class=HTMLResponse)
async def registrar_page(request: Request):
    return templates.TemplateResponse(request=request, name="registrar.html")