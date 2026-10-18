export interface User {
  id: number;
  name: string;
  email: string;
  role?: "user" | "admin";
  profile_photo_available?: boolean;
}

export interface LoginInput {
  email: string;
  password: string;
}

export interface RegisterInput {
  name: string;
  email: string;
  password: string;
  confirmPassword: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
}
