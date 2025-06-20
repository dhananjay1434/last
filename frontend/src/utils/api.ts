import axios, { AxiosResponse } from 'axios';
import {
  StatusResponse,
  ExtractResponse,
  JobStatus,
  StudyGuideResponse,
  SlidesResponse,
  ExtractionRequest,
  ApiError
} from '../types';

const API_BASE_URL: string = process.env.REACT_APP_API_URL || 'https://slide-extractor-api.onrender.com';

// Create axios instance with default config
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// API response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const apiError: ApiError = {
      error: error.response?.data?.error || error.message,
      message: error.response?.data?.message,
      status_code: error.response?.status,
    };
    return Promise.reject(apiError);
  }
);

// API functions
export const checkApiStatus = async (): Promise<StatusResponse> => {
  const response: AxiosResponse<StatusResponse> = await apiClient.get('/api/status');
  return response.data;
};

export const startExtraction = async (request: ExtractionRequest): Promise<ExtractResponse> => {
  const response: AxiosResponse<ExtractResponse> = await apiClient.post('/api/extract', request);
  return response.data;
};

export const getJobStatus = async (jobId: string): Promise<JobStatus> => {
  const response: AxiosResponse<JobStatus> = await apiClient.get(`/api/jobs/${jobId}`);
  return response.data;
};

export const getJobSlides = async (jobId: string): Promise<SlidesResponse> => {
  const response: AxiosResponse<SlidesResponse> = await apiClient.get(`/api/jobs/${jobId}/slides`);
  return response.data;
};

export const downloadJobPdf = async (jobId: string): Promise<Blob> => {
  const response: AxiosResponse<Blob> = await apiClient.get(`/api/jobs/${jobId}/pdf`, {
    responseType: 'blob',
  });
  return response.data;
};

export const getStudyGuide = async (jobId: string): Promise<StudyGuideResponse> => {
  const response: AxiosResponse<StudyGuideResponse> = await apiClient.get(`/api/jobs/${jobId}/study-guide`);
  return response.data;
};

// Utility functions
export const downloadFile = (blob: Blob, filename: string): void => {
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', filename);
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
};

export const openStudyGuideInNewWindow = (content: string, jobId: string): void => {
  const newWindow = window.open();
  if (newWindow) {
    newWindow.document.write(`
      <html>
        <head>
          <title>Study Guide - Job ${jobId}</title>
          <style>
            body {
              font-family: Arial, sans-serif;
              padding: 20px;
              line-height: 1.6;
              max-width: 800px;
              margin: 0 auto;
            }
            pre {
              white-space: pre-wrap;
              background-color: #f5f5f5;
              padding: 15px;
              border-radius: 5px;
              border-left: 4px solid #007acc;
            }
          </style>
        </head>
        <body>
          <h1>Study Guide - Job ${jobId}</h1>
          <pre>${content}</pre>
        </body>
      </html>
    `);
  }
};

export default apiClient;
