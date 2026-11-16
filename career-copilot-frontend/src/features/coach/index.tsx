import { useEffect, useRef, useState } from "react"
import {
  useCreateInterview,
  useInterview,
  useSendInterviewMessage,
} from "@/features/coach/hooks"
import type {
  InterviewMessageResponse,
  InterviewSessionResponse,
  StartInterviewRequest,
} from "@/features/coach/types"
import { useJobMatches } from "@/features/jobmatch/hooks"
import { EmptyState, ErrorState, Skeleton } from "@/shared/components"
import { ModuleHeader } from "@/shared/ModuleHeader"
import { Astro, Button, Icon } from "@/shared/ui"
import type { Module } from "@/shared/types"

function CoachSkeleton() {
  return (
    <>
      <ModuleHeader
        title="Entrena con Astro"
        copy="Practica en un entorno seguro y recibe feedback accionable en tiempo real."
      />
      <div className="coach-layout" aria-busy="true">
        <section className="chat-panel coach-loading-chat">
          <div className="chat-header">
            <Skeleton width={48} height={48} variant="circle" />
            <div><Skeleton width={150} height={15} /><Skeleton width={180} height={10} /></div>
          </div>
          <div className="chat-messages">
            <Skeleton width="68%" height={82} />
            <Skeleton width="72%" height={72} />
            <Skeleton width="61%" height={82} />
          </div>
          <div className="chat-compose"><Skeleton width="100%" height={48} /></div>
        </section>
        <aside className="session-panel coach-loading-session">
          <Skeleton width={88} height={70} />
          <Skeleton width="100%" height={110} />
          <Skeleton width="100%" height={66} />
          <Skeleton width="100%" height={42} />
        </aside>
      </div>
    </>
  )
}

function CoachStartSkeleton() {
  return (
    <>
      <ModuleHeader
        title="Entrena con Astro"
        copy="Practica en un entorno seguro y recibe feedback accionable en tiempo real."
      />
      <section className="coach-start-card" aria-busy="true">
        <div className="coach-start-loading coach-start-content">
          <div className="coach-start-loading-form">
            <Skeleton width="58%" height={22} />
            <Skeleton width="84%" height={12} variant="text" />
            <Skeleton width="100%" height={42} />
            <Skeleton width="76%" height={12} variant="text" />
            <Skeleton width={190} height={44} />
          </div>
          <Skeleton width={78} height={78} variant="circle" />
        </div>
      </section>
    </>
  )
}

function scoreSummary(session: InterviewSessionResponse): number | null {
  if (typeof session.score === "number") return session.score
  const scores = session.messages
    .map((message) => message.score)
    .filter((score): score is number => typeof score === "number")
  return scores.length
    ? Math.round(scores.reduce((total, score) => total + score, 0) / scores.length)
    : null
}

function ChatBubble({ message }: { message: InterviewMessageResponse }) {
  return (
    <div className={`chat-message ${message.role === "Astro" ? "astro" : "user"}`}>
      {message.role === "Astro" && (
        <div className="tiny-astro astro-face">
          <Astro size="small" pose="interviewer" />
        </div>
      )}
      <div>
        <div className="bubble">{message.content}</div>
        {message.score != null && (
          <div className="feedback-box">
            <div className="feedback-score">
              <b>{message.score}</b>
              <span>/100</span>
            </div>
            <p>
              <b>Feedback de Astro</b>
              {message.feedback ?? "Sigue practicando y apoya tus respuestas con ejemplos concretos."}
            </p>
            <span className="feedback-label">Feedback de respuesta</span>
          </div>
        )}
      </div>
    </div>
  )
}

export function CoachModule({ setActive }: { setActive: (module: Module) => void }) {
  const [jobAnalysisId, setJobAnalysisId] = useState("")
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [input, setInput] = useState("")
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const chatEndRef = useRef<HTMLDivElement>(null)
  const startController = useRef<AbortController | null>(null)
  const messageController = useRef<AbortController | null>(null)
  const jobsQuery = useJobMatches()
  const jobs = jobsQuery.data ?? []
  const selectedJob = jobs.find((job) => job.id === jobAnalysisId) ?? jobs[0]
  const createSession = useCreateInterview()
  const interviewQuery = useInterview(sessionId)
  const sendMessage = useSendInterviewMessage(sessionId)
  const session = interviewQuery.data
  const messages = session?.messages ?? []
  const isCompleted = session?.completedAt !== null && session?.completedAt !== undefined

  useEffect(() => {
    if (chatEndRef.current && typeof chatEndRef.current.scrollIntoView === "function") {
      chatEndRef.current.scrollIntoView({ behavior: "smooth", block: "end" })
    }
  }, [messages.length, sendMessage.isPending])

  useEffect(() => () => {
    startController.current?.abort()
    messageController.current?.abort()
  }, [])

  const startInterview = (request?: StartInterviewRequest) => {
    const payload = request ?? (selectedJob
      ? { targetRole: selectedJob.jobTitle, jobMatchId: selectedJob.id }
      : null)
    if (
      !payload?.targetRole.trim() ||
      !payload.jobMatchId ||
      startController.current ||
      createSession.isPending
    ) {
      return
    }

    const controller = new AbortController()
    startController.current = controller
    setInput("")
    createSession.mutate(
      { request: payload, signal: controller.signal },
      {
        onSuccess: ({ id }) => setSessionId(id),
        onSettled: () => {
          if (startController.current === controller) startController.current = null
        },
      },
    )
  }

  const submitMessage = (content: string) => {
    if (!sessionId || !content || messageController.current || sendMessage.isPending) return
    const controller = new AbortController()
    messageController.current = controller
    sendMessage.mutate(
      { content, signal: controller.signal },
      {
        onSuccess: () => setInput(""),
        onSettled: () => {
          if (messageController.current === controller) messageController.current = null
        },
      },
    )
  }

  const send = () => submitMessage(input.trim())

  if (!sessionId && jobsQuery.isLoading) return <CoachStartSkeleton />

  if (sessionId && interviewQuery.isLoading) return <CoachSkeleton />

  if (sessionId && interviewQuery.isError) {
    return (
      <>
        <ModuleHeader
          title="Entrena con Astro"
          copy="Practica en un entorno seguro y recibe feedback accionable en tiempo real."
        />
        <ErrorState
          title="No se pudo cargar la entrevista"
          message={interviewQuery.error.message}
          onRetry={() => void interviewQuery.refetch()}
          error={interviewQuery.error}
        />
      </>
    )
  }

  const averageScore = session ? scoreSummary(session) : null
  const userAnswers = messages.filter((message) => message.role === "Candidate").length

  return (
    <>
      <ModuleHeader
        title="Entrena con Astro"
        copy="Practica en un entorno seguro y recibe feedback accionable en tiempo real."
      />
      {!sessionId && jobsQuery.isError && (
        <ErrorState
          title="No se pudieron cargar las ofertas analizadas"
          message={jobsQuery.error.message}
          onRetry={() => void jobsQuery.refetch()}
          error={jobsQuery.error}
        />
      )}
      {createSession.isError && (
        <ErrorState
          title="No se pudo iniciar la entrevista"
          message={createSession.error.message}
          error={createSession.error}
          onRetry={() => {
            const request = createSession.variables?.request
            if (request) startInterview(request)
          }}
        />
      )}
      {!sessionId && !jobsQuery.isError && (
        <section className="coach-start-card">
          {createSession.isPending ? (
            <div className="coach-starting" role="status" aria-live="polite">
              <Skeleton width={48} height={48} variant="circle" />
              <span>Astro está pensando y preparando la primera pregunta...</span>
              <span className="letter-progress-track"><i /></span>
            </div>
          ) : (
            jobs.length === 0 ? (
              <EmptyState
                title="Primero analiza una oferta en JobMatch"
                description="Astro prepara la práctica usando el registro de JobMatch y sus requisitos. Solo puedes iniciar una entrevista con una oferta analizada."
                actionLabel="Ir a JobMatch"
                onAction={() => setActive("jobmatch")}
              >
                <div className="coach-start-empty-astro">
                  <Astro size="small" pose="think" />
                  <span>Astro te espera para practicar.</span>
                </div>
              </EmptyState>
            ) : (
              <EmptyState
                title="Tu próxima entrevista empieza aquí"
                description="Elige un registro de JobMatch. La práctica se personaliza con el CV y los requisitos de esa oferta."
              >
                <div className="coach-start-content">
                  <div className="coach-start-offer">
                    <label className="coach-job-label" htmlFor="coach-job-match">
                      <Icon name="target" size={16} />
                      Oferta analizada en JobMatch
                      <span>Obligatoria</span>
                    </label>
                    <select
                      id="coach-job-match"
                      value={selectedJob?.id ?? ""}
                      disabled={createSession.isPending}
                      onChange={(event) => setJobAnalysisId(event.currentTarget.value)}
                    >
                      {jobs.map((job) => (
                        <option value={job.id} key={job.id}>
                          {job.jobTitle}{job.company ? ` · ${job.company}` : ""}
                        </option>
                      ))}
                    </select>
                    <p className="coach-job-note">Solo puedes iniciar la entrevista con una oferta guardada en JobMatch.</p>
                    <Button
                      icon="arrow"
                      onClick={() => startInterview()}
                      disabled={!selectedJob || createSession.isPending}
                    >
                      Comenzar entrevista
                    </Button>
                  </div>
                  <div className="coach-start-astro" aria-label="Astro, tu entrenador de entrevistas">
                    <Astro size="small" pose="interviewer" />
                    <span>Astro</span>
                  </div>
                </div>
              </EmptyState>
            )
          )}
        </section>
      )}
      {session && (
        <div className="coach-layout">
          <section className="chat-panel">
            <div className="chat-header">
              <div className="astro-avatar">
                <Astro size="small" pose="interviewer" />
                <span />
              </div>
              <div>
                <h3>Astro · Reclutador IA</h3>
                <p>
                  {isCompleted ? "Entrevista finalizada" : "Entrevista en curso"}
                  {" · "}
                  {userAnswers} {userAnswers === 1 ? "respuesta" : "respuestas"}
                </p>
              </div>
              <span className="live-badge">{isCompleted ? "FINALIZADA" : "EN VIVO"}</span>
            </div>
            <div className="chat-messages" aria-live="polite">
              {messages.length === 0 ? (
                <EmptyState
                  title="La conversación aparecerá aquí"
                  description="Cuando Astro envíe la primera pregunta, podrás responder desde el cuadro de texto."
                />
              ) : (
                messages.map((message, index) => (
                  <ChatBubble key={message.id || `${message.role}-${index}`} message={message} />
                ))
              )}
              {sendMessage.isPending && (
                <div className="coach-reply-progress" role="status" aria-live="polite">
                  <span className="tiny-astro"><Icon name="spark" /></span>
                  <span className="typing-bubble" aria-hidden="true"><i /><i /><i /></span>
                  <span className="sr-only">Astro está escribiendo...</span>
                </div>
              )}
              <div ref={chatEndRef} />
            </div>
            {sendMessage.isError && (
              <ErrorState
                title="No se pudo enviar tu respuesta"
                message={sendMessage.error.message}
                error={sendMessage.error}
                onRetry={() => {
                  const content = sendMessage.variables?.content
                  if (content) submitMessage(content)
                }}
              />
            )}
            {isCompleted ? (
              <EmptyState
                title="Práctica finalizada"
                description="Ya puedes revisar tus respuestas y el feedback de Astro."
                actionLabel="Iniciar otra práctica"
                onAction={() => {
                  setSessionId(null)
                  setInput("")
                  createSession.reset()
                  sendMessage.reset()
                }}
              />
            ) : (
              <div className="chat-compose">
                <textarea
                  ref={textareaRef}
                  rows={2}
                  value={input}
                  disabled={sendMessage.isPending}
                  maxLength={10_000}
                  onChange={(event) => setInput(event.currentTarget.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" && !event.shiftKey) {
                      event.preventDefault()
                      send()
                    }
                  }}
                  placeholder="Escribe tu respuesta..."
                  aria-label="Respuesta de entrevista"
                />
                <button
                  type="button"
                  onClick={send}
                  disabled={!input.trim() || sendMessage.isPending}
                  aria-label="Enviar mensaje"
                >
                  <Icon name="send" />
                </button>
              </div>
            )}
          </section>
          <aside className="session-panel">
            {averageScore == null ? (
              <EmptyState
                title="Tu feedback aparecerá aquí"
                description="Responde a las preguntas de Astro para recibir una evaluación de tu práctica."
              />
            ) : (
              <>
                <div className="session-score">
                  <div>
                    <b>{averageScore}</b>
                    <small>/100</small>
                  </div>
                  <p>{averageScore >= 80 ? "Vas muy bien" : "Sigue practicando"}</p>
                </div>
                {session.feedback && (
                  <div className="coach-note">
                    <Icon name="spark" />
                    <p><b>Foco para mejorar</b>{session.feedback}</p>
                  </div>
                )}
              </>
            )}
          </aside>
        </div>
      )}
    </>
  )
}
