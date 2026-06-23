import request from './request'

export interface User {
  id: string
  username: string
  email?: string
  role: 'admin' | 'annotator' | 'reviewer'
  is_active: boolean
  is_password_changed: boolean
  created_at: string
  updated_at: string
}

export interface CreateUserRequest {
  username: string
  password?: string
  email?: string
  role: 'admin' | 'annotator' | 'reviewer'
}

export interface UpdateUserRequest {
  email?: string
  role?: 'admin' | 'annotator' | 'reviewer'
  is_active?: boolean
  password?: string
}

export interface LoginRequest {
  username: string
  password: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
}

export interface GetCurrentUserResponse extends User {}

export const usersApi = {
  login: (data: LoginRequest) =>
    request.post<LoginResponse>('/users/login/json', data),

  getCurrentUser: () =>
    request.get<GetCurrentUserResponse>('/users/me'),

  listUsers: (skip = 0, limit = 100) =>
    request.get<User[]>('/users/', { params: { skip, limit } }),

  getUser: (id: string) =>
    request.get<User>(`/users/${id}`),

  createUser: (data: CreateUserRequest) =>
    request.post<User>('/users/', data),

  updateUser: (id: string, data: UpdateUserRequest) =>
    request.put<User>(`/users/${id}`, data),

  deleteUser: (id: string) =>
    request.delete<void>(`/users/${id}`),
}

export default usersApi
