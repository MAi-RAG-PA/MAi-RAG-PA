// src/api/agent.ts
import apiClient from './client';

export interface AgentRequest {
  query: string;
  filename?: string;
}

export interface AgentResponse {
  status: string;
  message: string;
  content: string;
}

export const sendAgentRequest = async (data: AgentRequest): Promise<AgentResponse> => {
  const response = await apiClient.post('/api/agent', data);
  return response.data;
};
