export function buildGmailComposeUrl(
  recipient: string,
  subject: string,
  body: string,
): string {
  const url = new URL("https://mail.google.com/mail/u/0/")
  url.searchParams.set("fs", "1")
  url.searchParams.set("to", recipient)
  url.searchParams.set("su", subject)
  url.searchParams.set("body", body)
  url.searchParams.set("tf", "cm")
  return url.toString()
}
