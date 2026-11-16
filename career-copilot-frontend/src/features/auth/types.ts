export interface AuthCredentials {
  email: string
  password: string
}

export interface SignUpCredentials extends AuthCredentials {
  fullName: string
}

export interface AuthResponse {
  access_token: string
  expires_at: number
  user: {
    id: string
    email: string
    user_metadata?: { full_name?: string; name?: string }
  }
}
