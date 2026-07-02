export type AuthStatus = {
  configured: boolean;
};

export type LoginResult = {
  token: string;
  token_type: string;
  expires_at: string;
};

export type AuthSession = {
  authenticated: boolean;
  created_at: string;
  expires_at: string;
  last_used_at: string;
};

export type MessageResult = {
  message: string;
};
