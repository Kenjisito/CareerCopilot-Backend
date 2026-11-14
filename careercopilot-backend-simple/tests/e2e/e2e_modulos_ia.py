"""Recorrido E2E de los módulos con IA: Diagnóstico ATS (desglose del puntaje),
Job Match (extracción desde URL + recomendaciones) y entrevista completa con
evaluación final. Requiere los servicios levantados como indica README.md.

La extracción usa una oferta REAL de Computrabajo (necesita internet); si no
hay conexión, ese paso se informa y el recorrido sigue con texto pegado.

Uso: python tests/e2e/e2e_modulos_ia.py [mobile]"""
import os, re, sys, time
import httpx
from playwright.sync_api import sync_playwright

BASE = "http://localhost:3000"
S = os.environ.get("SHOTS_DIR", "./shots/")
CV = "./tests/e2e/cv_test.docx"
mobile = len(sys.argv) > 1 and sys.argv[1] == "mobile"
tag = "m_" if mobile else "d_"
vp = {"width": 390, "height": 844} if mobile else {"width": 1440, "height": 900}
os.makedirs(S, exist_ok=True)
problems, checks = [], []


def check(name, ok):
    checks.append((name, bool(ok)))
    print(("  OK   " if ok else "  FAIL ") + name, flush=True)


def real_offer_url():
    try:
        html = httpx.get("https://cl.computrabajo.com/trabajo-de-desarrollador", timeout=15,
                         headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"},
                         follow_redirects=True).text
        m = re.search(r'href="(/ofertas-de-trabajo/[^"#?]+)', html)
        return "https://cl.computrabajo.com" + m.group(1) if m else None
    except Exception:
        return None


with sync_playwright() as p:
    b = p.chromium.launch(executable_path=os.environ.get("CHROMIUM_PATH") or None)
    page = b.new_context(viewport=vp).new_page()
    # Los 4xx esperados (p. ej. la URL interna rechazada a propósito) no cuentan como problema.
    page.on("console", lambda m: problems.append(("console", m.type, m.text[:200])) if m.type == "error" and "status of 4" not in m.text else None)
    page.on("pageerror", lambda e: problems.append(("pageerror", str(e)[:200])))
    page.on("response", lambda r: problems.append(("http", r.status, r.url)) if r.status >= 500 else None)
    shot = lambda n: page.screenshot(path=f"{S}{tag}{n}.png", full_page=True)

    print("STEP registro")
    page.goto(BASE + "/register")
    inputs = page.locator("form input")
    inputs.nth(0).fill("Prueba IA"); inputs.nth(1).fill(f"ia{tag}{time.time():.0f}@test.cl"); inputs.nth(2).fill("clave-segura-1")
    page.click("button[type=submit]"); page.wait_for_url("**/dashboard", timeout=15000)

    print("STEP diagnóstico ATS")
    page.goto(BASE + "/ats"); page.set_input_files("input[type=file]", CV)
    page.wait_for_selector("text=Cómo se calculó tu puntaje", timeout=15000)
    main = page.inner_text("main")
    check("ATS muestra puntaje 74", "74" in main)
    check("ATS muestra desglose (5 criterios)", all(k in main for k in ["Estructura y secciones", "Datos de contacto", "Experiencia y logros", "Habilidades y palabras clave", "Formato y legibilidad ATS"]))
    check("ATS muestra perfil detectado", "Perfil detectado" in main)
    shot("ia_01_ats")

    print("STEP job match: URL inválida")
    page.goto(BASE + "/job-match"); page.wait_for_selector("#job-url")
    extract_btn = page.get_by_role("button", name=re.compile("Extraer"))
    check("Extraer deshabilitado sin URL", extract_btn.is_disabled())
    page.fill("#job-url", "http://192.168.1.1/admin"); extract_btn.click()
    try:
        page.get_by_text(re.compile("no apunta a un sitio público")).wait_for(timeout=15000)
        check("URL interna rechazada con mensaje", True)
    except Exception:
        check("URL interna rechazada con mensaje", False)
    shot("ia_02_jm_url_error")

    print("STEP job match: URL real")
    url = real_offer_url()
    if url:
        page.fill("#job-url", url); extract_btn.click()
        try:
            page.wait_for_selector("text=Oferta importada desde", timeout=25000)
            check("Oferta real importada (nombre)", len(page.input_value("#job-name")) > 3)
            check("Oferta real importada (texto)", len(page.input_value("#job-description")) > 100)
        except Exception:
            check("Oferta real importada", False)
            print("   aviso:", page.inner_text("main")[:300])
        shot("ia_03_jm_importada")
    else:
        print("  (sin internet: se omite la extracción real)")
    if len(page.input_value("#job-description")) < 100:
        page.fill("#job-name", "Backend Dev — Acme")
        page.fill("#job-description", "Buscamos desarrollador backend Python FastAPI con SQL y Docker, deseable AWS y Kubernetes")

    page.get_by_role("button", name=re.compile("Calcular compatibilidad")).click()
    page.wait_for_selector("text=Recomendaciones para esta postulación", timeout=15000)
    check("Job Match muestra recomendaciones", "Destaca tus APIs" in page.inner_text("main"))
    shot("ia_04_jm_resultado")

    print("STEP entrevista completa")
    page.get_by_role("button", name=re.compile("Practicar entrevista")).click(); page.wait_for_url("**/entrevista?id=*")
    page.select_option("#tipo", "tecnica"); page.select_option("#nivel", "Senior")
    page.get_by_role("button", name=re.compile("Iniciar simulación")).click()
    page.wait_for_selector("text=Pregunta 1 de 6", timeout=15000)
    check("Terminar deshabilitado sin respuestas", page.get_by_role("button", name=re.compile("Terminar y evaluar")).is_disabled())
    shot("ia_05_int_inicio")
    for n in range(1, 7):
        page.fill("textarea", f"Respuesta {n}: en Acme lideré una API con FastAPI que redujo la latencia un 40%.")
        page.keyboard.press("Enter")
        if n < 6:
            page.wait_for_selector(f"text=Pregunta {n + 1} de 6", timeout=15000)
    page.wait_for_selector("text=Evaluación de tu entrevista", timeout=20000)
    main = page.inner_text("main")
    check("Evaluación con puntaje y nivel", "/ 100 puntos" in main)
    check("Evaluación: 6 de 6 preguntas", "Respondiste 6 de 6" in main)
    check("Evaluación muestra competencias", "Ejemplos concretos (STAR)" in main)
    check("Evaluación muestra recomendaciones", "Cuantifica tus logros" in main)
    page.get_by_role("button", name=re.compile(r"1\. ")).first.click(); page.wait_for_timeout(400)
    check("Detalle por pregunta muestra la respuesta del usuario", "Respuesta 1: en Acme" in page.inner_text("main"))
    shot("ia_06_int_evaluacion")
    b.close()

print("\nRESUMEN:", sum(ok for _, ok in checks), "/", len(checks), "comprobaciones OK")
print("PROBLEMAS EN EL NAVEGADOR:", problems or "ninguno")
sys.exit(0 if all(ok for _, ok in checks) and not problems else 1)
