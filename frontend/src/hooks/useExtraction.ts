import { useState, useEffect, useCallback } from 'react';
import {
  ApiStatus,
  ExtractionOptions,
  JobStatus,
  ExtractionRequest,
  ApiError
} from '../types';
import {
  checkApiStatus as checkApiStatusAPI,
  startExtraction as startExtractionAPI,
  getJobStatus as getJobStatusAPI,
  downloadJobPdf,
  getStudyGuide,
  downloadFile,
  openStudyGuideInNewWindow
} from '../utils/api';

interface UseExtractionReturn {
  // State
  apiStatus: ApiStatus;
  videoUrl: string;
  extractionOptions: ExtractionOptions;
  geminiApiKey: string;
  currentJob: string | null;
  jobStatus: JobStatus | null;
  isExtracting: boolean;
  
  // Actions
  setVideoUrl: (url: string) => void;
  setExtractionOptions: (options: ExtractionOptions | ((prev: ExtractionOptions) => ExtractionOptions)) => void;
  setGeminiApiKey: (key: string) => void;
  startExtraction: () => Promise<void>;
  checkJobStatus: (jobId: string) => Promise<void>;
  downloadPdf: () => Promise<void>;
  viewStudyGuide: () => Promise<void>;
  refreshApiStatus: () => Promise<void>;
}

export const useExtraction = (): UseExtractionReturn => {
  // State
  const [apiStatus, setApiStatus] = useState<ApiStatus>({ 
    online: false, 
    message: 'Checking...' 
  });
  const [videoUrl, setVideoUrl] = useState<string>('');
  const [extractionOptions, setExtractionOptions] = useState<ExtractionOptions>({
    adaptive_sampling: true,
    extract_content: true,
    organize_slides: true,
    generate_pdf: true,
    enable_transcription: false,
    enable_ocr_enhancement: false,
    enable_concept_extraction: false,
    enable_slide_descriptions: false
  });
  const [geminiApiKey, setGeminiApiKey] = useState<string>('');
  const [currentJob, setCurrentJob] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<JobStatus | null>(null);
  const [isExtracting, setIsExtracting] = useState<boolean>(false);

  // Check API status
  const refreshApiStatus = useCallback(async (): Promise<void> => {
    try {
      const response = await checkApiStatusAPI();
      setApiStatus({
        online: true,
        message: `✅ API Online - Features: ${Object.entries(response)
          .filter(([key, value]) => key !== 'status' && value)
          .map(([key]) => key.replace('_', ' '))
          .join(', ')}`
      });
    } catch (error: any) {
      setApiStatus({
        online: false,
        message: `❌ API Offline: ${error.error || error.message}`
      });
    }
  }, []);

  // Start extraction
  const startExtraction = useCallback(async (): Promise<void> => {
    if (!videoUrl.trim()) {
      throw new Error('Please enter a video URL');
    }

    setIsExtracting(true);
    try {
      const request: ExtractionRequest = {
        video_url: videoUrl.trim(),
        ...extractionOptions
      };

      if (geminiApiKey.trim()) {
        request.gemini_api_key = geminiApiKey.trim();
      }

      const response = await startExtractionAPI(request);
      setCurrentJob(response.job_id);
      setJobStatus({
        status: 'initializing',
        progress: 0,
        message: 'Starting extraction...'
      });
    } catch (error: any) {
      setIsExtracting(false);
      throw new Error(`Error starting extraction: ${error.error || error.message}`);
    }
  }, [videoUrl, extractionOptions, geminiApiKey]);

  // Check job status
  const checkJobStatus = useCallback(async (jobId: string): Promise<void> => {
    try {
      const response = await getJobStatusAPI(jobId);
      setJobStatus(response);
      
      if (response.status === 'completed' || response.status === 'failed') {
        setIsExtracting(false);
      }
    } catch (error: any) {
      console.error('Error checking job status:', error);
    }
  }, []);

  // Download PDF
  const downloadPdf = useCallback(async (): Promise<void> => {
    if (!currentJob) return;
    
    try {
      const blob = await downloadJobPdf(currentJob);
      downloadFile(blob, `slides_job_${currentJob}.pdf`);
    } catch (error: any) {
      throw new Error(`Error downloading PDF: ${error.error || error.message}`);
    }
  }, [currentJob]);

  // View study guide
  const viewStudyGuide = useCallback(async (): Promise<void> => {
    if (!currentJob) return;
    
    try {
      const response = await getStudyGuide(currentJob);
      openStudyGuideInNewWindow(response.content, currentJob);
    } catch (error: any) {
      throw new Error(`Error getting study guide: ${error.error || error.message}`);
    }
  }, [currentJob]);

  // Auto-check API status on mount
  useEffect(() => {
    refreshApiStatus();
    const interval = setInterval(refreshApiStatus, 30000); // Check every 30 seconds
    return () => clearInterval(interval);
  }, [refreshApiStatus]);

  // Auto-poll job status when extracting
  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (currentJob && isExtracting) {
      interval = setInterval(() => {
        checkJobStatus(currentJob);
      }, 2000);
    }
    return () => clearInterval(interval);
  }, [currentJob, isExtracting, checkJobStatus]);

  return {
    // State
    apiStatus,
    videoUrl,
    extractionOptions,
    geminiApiKey,
    currentJob,
    jobStatus,
    isExtracting,
    
    // Actions
    setVideoUrl,
    setExtractionOptions,
    setGeminiApiKey,
    startExtraction,
    checkJobStatus,
    downloadPdf,
    viewStudyGuide,
    refreshApiStatus
  };
};
