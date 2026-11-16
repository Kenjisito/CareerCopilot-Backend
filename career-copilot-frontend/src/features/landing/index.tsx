import { Astro, Brand, Button, Icon } from "@/shared/ui"
import type { IconName } from "@/shared/types"

export function Landing({ onStart, onLogin }: { onStart: () => void; onLogin: () => void }) {
  return (
    <div className="landing">
      <header className="landing-nav">
        <Brand />
        <nav>
          <a href="#como-funciona">Cómo funciona</a>
          <a href="#beneficios">Beneficios</a>
          <a href="#recursos">Recursos</a>
        </nav>
        <div className="nav-actions">
          <button className="text-link" onClick={onLogin}>Iniciar sesión</button>
          <Button onClick={onStart}>Crear cuenta gratis</Button>
        </div>
      </header>
      <main>
        <section className="hero">
          <div className="hero-copy">
            <div className="eyebrow">
              <Icon name="spark" size={16} /> IA para tu próxima oportunidad
            </div>
            <h1>
              Tu carrera merece un <span>copiloto.</span>
            </h1>
            <p>
              Optimiza tu CV, descubre cuánto encajas en cada oferta y entrena
              entrevistas con Astro, tu asistente de carrera con IA.
            </p>
            <div className="hero-actions">
              <Button onClick={onStart} icon="arrow">
                Crear cuenta gratis
              </Button>
              <button className="play-link">
                <Icon name="play" size={16} /> Conoce a Astro
              </button>
            </div>
            <div className="social-proof">
              <div className="avatar-stack">
                <span>LM</span>
                <span>JP</span>
                <span>AC</span>
              </div>
              <div>
                <b>+2.500 candidatos</b>
                <small>ya aceleran su búsqueda</small>
              </div>
            </div>
          </div>
          <div className="hero-visual">
            <div className="astro-stage">
              <div className="status-chip">
                <span /> Astro está listo
              </div>
              <Astro pose="wave" />
              <div className="floating-card match-float">
                <div className="score-ring">88%</div>
                <div>
                  <b>Gran match</b>
                  <small>Senior Product Designer</small>
                </div>
              </div>
              <div className="floating-card insight-float">
                <Icon name="spark" />
                <span>
                  <b>Consejo de Astro</b>
                  <small>Destaca tu experiencia en research.</small>
                </span>
              </div>
            </div>
          </div>
        </section>
        <section className="steps" id="como-funciona">
          <div className="section-heading">
            <h2>De tu CV a tu próxima entrevista</h2>
            <p>Astro analiza, conecta y te prepara en tres pasos simples.</p>
          </div>
          <div className="step-grid">
            {[
              [
                "01",
                "upload",
                "Sube tu CV",
                "Importa tu experiencia en segundos. Astro organiza todo por ti.",
              ],
              [
                "02",
                "target",
                "Analiza tu JobMatch",
                "Compara tu perfil con cada oferta y descubre cómo destacar.",
              ],
              [
                "03",
                "message",
                "Prepara tu entrevista",
                "Practica respuestas y recibe feedback personalizado al instante.",
              ],
            ].map(([n, icon, title, copy], index) => (
              <div className="step-card" key={title}>
                <span className="step-number">{n}</span>
                <div className="step-icon">
                  <Icon name={icon as IconName} />
                </div>
                <h3>{title}</h3>
                <p>{copy}</p>
                {index < 2 && <div className="step-line" />}
              </div>
            ))}
          </div>
        </section>
        <section className="features" id="beneficios">
          <div className="feature-intro">
            <span className="eyebrow">
              <Icon name="spark" size={16} /> TODO EN UNA MISIÓN
            </span>
            <h2>Las herramientas que tu búsqueda necesitaba</h2>
            <p>
              Menos incertidumbre. Más decisiones inteligentes y oportunidades
              reales.
            </p>
            <Button onClick={onStart} variant="secondary" icon="arrow">
              Explorar la plataforma
            </Button>
          </div>
          <div className="feature-grid">
            <article className="feature-card feature-wide">
              <div className="feature-icon">
                <Icon name="document" />
              </div>
              <h3>CV preparado para ATS</h3>
              <p>
                Un perfil claro, optimizado y listo para superar los filtros
                automáticos.
              </p>
              <div className="mini-document">
                <span />
                <span />
                <span className="short" />
                <b>ATS READY</b>
              </div>
            </article>
            <article className="feature-card">
              <div className="feature-icon">
                <Icon name="target" />
              </div>
              <h3>JobMatch inteligente</h3>
              <p>
                Prioriza las oportunidades donde tienes más posibilidades de
                avanzar.
              </p>
              <div className="mini-chart">
                <i style={{ height: "42%" }} />
                <i style={{ height: "65%" }} />
                <i style={{ height: "52%" }} />
                <i style={{ height: "88%" }} />
              </div>
            </article>
            <article className="feature-card">
              <div className="feature-icon">
                <Icon name="mail" />
              </div>
              <h3>Mensajes que conectan</h3>
              <p>Cartas y emails personalizados para cada postulación.</p>
              <div className="mini-mail">
                <span />
                <span />
                <span />
                <em />
              </div>
            </article>
          </div>
        </section>
      </main>
      <footer>
        <Brand light />
        <p>Tu talento merece llegar más lejos.</p>
        <div>
          <a href="#producto">Producto</a>
          <a href="#privacidad">Privacidad</a>
          <a href="#ayuda">Ayuda</a>
        </div>
        <small>© 2025 Career Copilot</small>
      </footer>
    </div>
  )
}
