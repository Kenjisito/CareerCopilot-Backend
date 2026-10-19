import sys, re, json
from playwright.sync_api import sync_playwright, expect
BASE="http://localhost:3000"; S="./shots/"
CV="./tests/e2e/cv_test.docx"
mobile = len(sys.argv)>1 and sys.argv[1]=="mobile"
tag = "m_" if mobile else "d_"
vp = {"width":390,"height":844} if mobile else {"width":1440,"height":900}
problems=[]
def shot(page,name): page.screenshot(path=f"{S}{tag}{name}.png", full_page=True)
with sync_playwright() as p:
    b=p.chromium.launch(executable_path=__import__("os").environ.get("CHROMIUM_PATH") or None)
    ctx=b.new_context(viewport=vp); page=ctx.new_page()
    page.on("console", lambda m: problems.append(("console",m.type,m.text[:200])) if m.type in("error","warning") else None)
    page.on("pageerror", lambda e: problems.append(("pageerror",str(e)[:200])))
    page.on("requestfailed", lambda r: problems.append(("reqfailed",r.url,r.failure)))
    page.on("response", lambda r: problems.append(("http",r.status,r.url)) if r.status>=400 else None)
    def step(n): print("STEP",n, flush=True)

    step("guard"); page.goto(BASE+"/dashboard"); page.wait_for_url("**/login", timeout=8000); shot(page,"01_login")
    step("bad login"); page.fill('input[type=email]',"nadie@test.cl"); page.fill('input[type=password]',"mala-clave"); page.click('button[type=submit]')
    page.wait_for_selector('[role=alert]'); print("  alert:",page.inner_text('[role=alert]')); shot(page,"02_login_error")
    step("register"); page.goto(BASE+"/register")
    page.fill('input[placeholder*="ombre"]',"Kenji Prueba") if page.locator('input[placeholder*="ombre"]').count() else None
    inputs=page.locator('form input'); print("  inputs:",inputs.count())
    inputs.nth(0).fill("Kenji Prueba"); inputs.nth(1).fill(f"kenji{tag}{__import__('time').time():.0f}@test.cl"); inputs.nth(2).fill("clave-segura-1")
    shot(page,"03_register"); page.click('button[type=submit]'); page.wait_for_url("**/dashboard", timeout=10000)
    page.wait_for_selector("dl"); page.wait_for_timeout(500); shot(page,"04_dashboard")
    step("dashboard stats"); print("  ",page.inner_text("dl").replace("\n"," | "))
    step("ats"); page.goto(BASE+"/ats"); page.wait_for_timeout(800); shot(page,"05_ats_empty")
    page.set_input_files('input[type=file]',CV); page.wait_for_timeout(2500); shot(page,"06_ats_result")
    print("  ats text has score:", "74" in page.inner_text("main"))
    step("job-match"); page.goto(BASE+"/job-match"); page.wait_for_timeout(800); shot(page,"07_jm_empty")
    btn=page.get_by_role("button",name=re.compile("Calcular")); print("  button disabled initially:",btn.is_disabled())
    page.fill("#job-name","Backend Dev — Acme"); page.fill("#job-description","corta"); print("  disabled w/ short offer:",btn.is_disabled()); shot(page,"08_jm_short")
    page.fill("#job-description","Buscamos desarrollador backend Python FastAPI con SQL y Docker, deseable AWS y Kubernetes"); btn.click()
    page.wait_for_selector("text=COMPATIBLE", timeout=10000); shot(page,"09_jm_result")
    page.get_by_role("button",name=re.compile("Generar email")).click(); page.wait_for_url("**/email?id=*")
    step("email"); page.wait_for_timeout(800); shot(page,"10_email_empty")
    page.get_by_role("button",name=re.compile("Generar email")).click(); page.wait_for_selector("#subject", timeout=10000); shot(page,"11_email_draft")
    page.fill("#subject","Asunto editado"); page.get_by_role("button",name="Guardar").click(); page.wait_for_selector("text=Cambios guardados"); shot(page,"12_email_saved")
    step("historial"); page.goto(BASE+"/historial"); page.wait_for_selector("text=Backend Dev"); page.get_by_text("Backend Dev").first.click(); page.wait_for_selector("text=Oferta analizada"); shot(page,"13_hist_detail")
    step("entrevista"); page.get_by_role("button",name=re.compile("Entrevista IA")).first.click(); page.wait_for_url("**/entrevista?id=*"); page.wait_for_timeout(600); shot(page,"14_int_setup")
    page.get_by_role("button",name=re.compile("Iniciar simulación")).click(); page.wait_for_selector("text=FastAPI", timeout=10000)
    page.fill("textarea","Usé FastAPI para una API de reservas con 5 mil usuarios."); page.keyboard.press("Enter"); page.wait_for_selector("text=Usé FastAPI", timeout=5000); page.wait_for_timeout(1500); shot(page,"15_int_chat")
    page.get_by_role("button",name="Finalizar").click(); page.wait_for_selector("text=Terminaste esta entrevista"); shot(page,"16_int_done")
    step("delete from historial"); page.goto(BASE+"/historial"); page.wait_for_selector("text=Backend Dev")
    page.get_by_role("button",name=re.compile("Eliminar")).first.click(); shot(page,"17_hist_confirm"); page.get_by_role("button",name="Confirmar").click(); page.wait_for_selector("text=Aún no tienes análisis", timeout=8000); shot(page,"18_hist_empty")
    step("job-match tras eliminar"); 
    step("logout")
    if mobile:
        page.goto(BASE+"/dashboard"); page.get_by_label("Abrir navegación").click(); page.wait_for_timeout(300); shot(page,"19_mobile_menu")
    page.get_by_role("button",name=re.compile("Cerrar sesión")).first.click(); page.wait_for_url("**/login"); page.goto(BASE+"/dashboard"); page.wait_for_url("**/login", timeout=8000); print("  guard after logout ok")
    step("landing"); page.goto(BASE+"/"); page.wait_for_timeout(800); shot(page,"20_landing")
    b.close()
print("PROBLEMS:"); [print(" ",x) for x in problems]
