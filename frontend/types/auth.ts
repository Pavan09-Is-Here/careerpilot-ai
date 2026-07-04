export type AuthStatus = {
  configured: boolean;
  registration_open?: boolean;
};

export type RegisterInput = {
  username: string;
  password: string;
  full_name: string;
  email: string;
};

export type LoginResult = {
  token: string;
  token_type: string;
  expires_at: string;
  username: string;
};

export type AuthSession = {
  authenticated: boolean;
  username: string;
  email: string | null;
  email_verified: boolean;
  created_at: string;
  expires_at: string;
  last_used_at: string;
};

export type MessageResult = {
  message: string;
};
