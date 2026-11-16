import sys, re, time, json, urllib.request
from playwright.sync_api import sync_playwright
BASE="http://localhost:3000"; S="./shots/"; CV="./tests/e2e/cv_test.docx"
mobile = len(sys.argv)>1 and sys.argv[1]=="mobile"
tag = "n_m_" if mobile else "n_d_"
vp = {"width":390,"height":844} if mobile else {"width":1440,"height":900}
problems=[]
def shot(page,name): page.screenshot(path=f"{S}{tag}{name}.png", full_page=True)
def step(n): print("STEP",n,flush=True)
def get(url): return json.load(urllib.request.urlopen(urllib.request.Request(url)))
import os; os.environ["NO_PROXY"]="127.0.0.1,localhost"
urllib.request.install_opener(urllib.request.build_opener(urllib.request.ProxyHandler({})))
email=f"nuevo{tag}{int(time.time())}@test.cl"
with sync_playwright() as p:
    b=p.chromium.launch(executable_path=__import__("os").environ.get("CHROMIUM_PATH") or None)
    ctx=b.new_context(viewport=vp); page=ctx.new_page()
    page.on("pageerror", lambda e: problems.append(("pageerror",str(e)[:200])))
    page.on("response", lambda r: problems.append(("http",r.status,r.url)) if r.status>=400 else None)

    step("registro"); page.goto(BASE+"/register"); i=page.locator("form input")
    i.nth(0).fill("Kenji Prueba"); i.nth(1).fill(email); i.nth(2).fill("clave-segura-1"); page.click("button[type=submit]"); page.wait_for_url("**/dashboard")
    page.wait_for_selector("dl"); print("  ",page.inner_text("dl").replace("\n"," | "))
    step("logout"); 
    if mobile: page.get_by_label("Abrir navegación").click()
    page.get_by_role("button",name="Cerrar sesión").last.click(); page.wait_for_url("**/login")

    step("olvidé contraseña"); page.click("text=¿Olvidaste tu contraseña?"); page.wait_for_url("**/forgot-password"); shot(page,"01_forgot")
    page.fill("#email",email); page.click("button[type=submit]"); page.wait_for_selector("text=Si existe una cuenta"); shot(page,"02_forgot_sent")
    print("  recoveries:",get("http://127.0.0.1:9000/__recoveries")[-1:])

    step("reset enlace inválido"); page.goto(BASE+"/reset-password"); page.wait_for_selector("text=no es válido",timeout=6000); shot(page,"03_reset_invalid")

    step("reset con token"); s=get(f"http://127.0.0.1:9000/__token?email={email}")
    page.goto("about:blank"); page.goto(f"{BASE}/reset-password#access_token={s['access_token']}&refresh_token={s['refresh_token']}&expires_in=3600&token_type=bearer&type=recovery")
    page.wait_for_selector("#password",timeout=8000); shot(page,"04_reset_form")
    page.fill("#password","otra-clave-123"); page.fill("#confirm","distinta-123"); page.click("button[type=submit]"); page.wait_for_selector("text=no coinciden")
    page.fill("#confirm","otra-clave-123"); page.click("button[type=submit]"); page.wait_for_selector("text=Contraseña actualizada"); shot(page,"05_reset_done")
    page.wait_for_url("**/login",timeout=8000)
    step("login con clave nueva"); page.fill('input[type=email]',email); page.fill('input[type=password]',"clave-segura-1"); page.click("button[type=submit]"); page.wait_for_selector('[role=alert]'); print("  clave vieja rechazada:",page.inner_text('[role=alert]'))
    page.fill('input[type=password]',"otra-clave-123"); page.click("button[type=submit]"); page.wait_for_url("**/dashboard")

    step("ats + historial"); page.goto(BASE+"/ats"); page.set_input_files('input[type=file]',CV); page.wait_for_selector("text=APROBADO",timeout=15000)
    step("pdf ats (print media)"); page.emulate_media(media="print"); page.wait_for_timeout(300)
    vis=page.locator("#print-root").inner_text(); print("  print-root:",vis[:120].replace("\n"," | ")); shot(page,"06_ats_print"); page.emulate_media(media="screen")
    page.get_by_role("button",name=re.compile("Analizar otro CV")).click(); page.wait_for_selector("text=Diagnósticos anteriores"); shot(page,"07_ats_history")
    page.locator("text=cv_test.docx").first.click(); page.wait_for_selector("text=APROBADO"); print("  detalle desde historial OK")

    step("email pdf"); page.goto(BASE+"/job-match"); page.fill("#job-name","Dev Backend"); page.fill("#job-description","Buscamos desarrollador backend Python FastAPI con SQL y Docker, deseable AWS y Kubernetes")
    page.get_by_role("button",name=re.compile("Calcular")).click(); page.wait_for_selector("text=COMPATIBLE",timeout=15000)
    page.get_by_role("button",name=re.compile("Generar email")).click(); page.wait_for_url("**/email?id=*")
    page.get_by_role("button",name=re.compile("Generar email")).click(); page.wait_for_selector("#subject",timeout=15000); shot(page,"08_email_actions")
    page.emulate_media(media="print"); page.wait_for_timeout(300); print("  email print:",page.locator("#print-root").inner_text()[:80].replace("\n"," | ")); shot(page,"09_email_print"); page.emulate_media(media="screen")

    step("perfil"); page.goto(BASE+"/perfil"); page.wait_for_selector("#name:not([disabled])"); page.wait_for_timeout(500); shot(page,"10_perfil")
    page.fill("#name","Kenji Romero"); page.get_by_role("button",name="Guardar cambios").click(); page.wait_for_selector("text=Perfil actualizado"); shot(page,"11_perfil_saved")
    page.reload(); page.wait_for_selector("#name:not([disabled])"); print("  nombre tras recargar:",page.input_value("#name"))
    if not mobile: print("  sidebar:",page.locator("aside").inner_text().replace("\n"," | ")[-80:])

    step("modo oscuro"); page.get_by_role("button",name="Oscuro",exact=True).click(); page.wait_for_timeout(300); shot(page,"12_perfil_dark")
    print("  html.dark:",page.evaluate("document.documentElement.classList.contains('dark')"))
    for name,path in [("13_dash_dark","/dashboard"),("14_ats_dark","/ats"),("15_hist_dark","/historial"),("16_jm_dark","/job-match"),("17_ent_dark","/entrevista")]:
        page.goto(BASE+path); page.wait_for_timeout(1200); shot(page,name)
    page.goto(BASE+"/login") if False else None
    page.reload(); print("  persiste tras recarga:",page.evaluate("document.documentElement.classList.contains('dark')"))
    page.evaluate("localStorage.setItem('cc_theme','light')")
    print("PROBLEMS:"); [print("  ",x) for x in problems]
    b.close()
