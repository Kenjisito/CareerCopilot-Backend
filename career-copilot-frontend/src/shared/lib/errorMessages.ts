const messages: Record<string, string> = {
  file_too_large: "El archivo supera el límite de 2 MB.",
  unsupported_file_type: "El archivo debe ser PDF o DOCX.",
  validation_error: "Revisa los datos ingresados e inténtalo nuevamente.",
  quota_exceeded: "Alcanzaste el límite de uso de tu plan.",
  unauthorized: "Tu sesión expiró. Inicia sesión nuevamente.",
  not_found: "No encontramos la información solicitada.",
  network_error: "No fue posible conectar con el servidor.",
}

export function getErrorMessage(code: string, fallback?: string): string {
  return messages[code] ?? fallback ?? "Ocurrió un error. Inténtalo nuevamente."
}
