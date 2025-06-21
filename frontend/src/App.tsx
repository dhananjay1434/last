import React, { useState, useEffect } from 'react';
import { Play, Download, FileText, Settings, CheckCircle, AlertCircle, Loader } from 'lucide-react';
import axios, { AxiosResponse } from 'axios';

// Types
interface ApiStatus {
  online: boolean;
  message: string;
}

interface ExtractionOptions {
  adaptive_sampling: boolean;
  extract_content: boolean;
  organize_slides: boolean;
  generate_pdf: boolean;
  enable_transcription: boolean;
  enable_ocr_enhancement: boolean;
  enable_concept_extraction: boolean;
  enable_slide_descriptions: boolean;
}

interface JobStatus {
  status: string;
  progress: number;
  message: string;
  error?: string;
  slides_count?: number;
  has_pdf?: boolean;
  has_study_guide?: boolean;
}

interface ExtractResponse {
  job_id: string;
  message: string;
}

interface StatusResponse {
  enhanced_features?: boolean;
  transcription?: boolean;
  ocr_enhancement?: boolean;
  advanced_features?: boolean;
  [key: string]: any;
}

interface StudyGuideResponse {
  content: string;
}

// Configuration
const API_BASE_URL: string = process.env.REACT_APP_API_URL || 'https://slide-extractor-api.onrender.com';

const App: React.FC = () => {
  const [apiStatus, setApiStatus] = useState<ApiStatus>({ online: false, message: 'Checking...' });
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
  const [isTestingVideo, setIsTestingVideo] = useState<boolean>(false);
  const [videoTestResult, setVideoTestResult] = useState<string | null>(null);

  // Check API status on component mount
  useEffect(() => {
    checkApiStatus();
    const interval = setInterval(checkApiStatus, 30000); // Check every 30 seconds
    return () => clearInterval(interval);
  }, []);

  // Poll job status when extraction is running
  useEffect(() => {
    let interval;
    if (currentJob && isExtracting) {
      interval = setInterval(() => {
        checkJobStatus(currentJob);
      }, 2000);
    }
    return () => clearInterval(interval);
  }, [currentJob, isExtracting]);

  const checkApiStatus = async (): Promise<void> => {
    try {
      const response: AxiosResponse<StatusResponse> = await axios.get(`${API_BASE_URL}/api/status`, { timeout: 10000 });
      setApiStatus({
        online: true,
        message: `✅ API Online - Features: ${Object.entries(response.data)
          .filter(([key, value]) => key !== 'status' && value)
          .map(([key]) => key.replace('_', ' '))
          .join(', ')}`
      });
    } catch (error: any) {
      setApiStatus({
        online: false,
        message: `❌ API Offline: ${error.message}`
      });
    }
  };

  const testVideoAccessibility = async (): Promise<void> => {
    if (!videoUrl.trim()) {
      alert('Please enter a video URL');
      return;
    }

    setIsTestingVideo(true);
    setVideoTestResult(null);

    try {
      const response = await axios.post(`${API_BASE_URL}/api/test-video`, {
        video_url: videoUrl.trim()
      });

      if (response.data.accessible) {
        setVideoTestResult(`✅ Video accessible: "${response.data.title}"`);
      } else {
        setVideoTestResult(`❌ ${response.data.message}. ${response.data.suggestion}`);
      }
    } catch (error: any) {
      setVideoTestResult(`❌ Error testing video: ${error.response?.data?.error || error.message}`);
    } finally {
      setIsTestingVideo(false);
    }
  };

  const startExtraction = async (): Promise<void> => {
    if (!videoUrl.trim()) {
      alert('Please enter a video URL');
      return;
    }

    setIsExtracting(true);
    setVideoTestResult(null);
    try {
      const requestData: any = {
        video_url: videoUrl.trim(),
        ...extractionOptions
      };

      if (geminiApiKey.trim()) {
        requestData.gemini_api_key = geminiApiKey.trim();
      }

      const response: AxiosResponse<ExtractResponse> = await axios.post(`${API_BASE_URL}/api/extract`, requestData);
      setCurrentJob(response.data.job_id);
      setJobStatus({
        status: 'initializing',
        progress: 0,
        message: 'Starting extraction...'
      });
    } catch (error: any) {
      setIsExtracting(false);
      const errorMessage = error.response?.data?.error || error.message;
      if (errorMessage.includes('bot detection') || errorMessage.includes('YouTube')) {
        alert(`YouTube Access Issue: ${errorMessage}\n\nTry:\n1. A different video\n2. A shorter video\n3. An educational channel video\n4. Testing the video first using the "Test Video" button`);
      } else {
        alert(`Error starting extraction: ${errorMessage}`);
      }
    }
  };

  const checkJobStatus = async (jobId: string): Promise<void> => {
    try {
      const response: AxiosResponse<JobStatus> = await axios.get(`${API_BASE_URL}/api/jobs/${jobId}`);
      setJobStatus(response.data);

      if (response.data.status === 'completed' || response.data.status === 'failed') {
        setIsExtracting(false);
      }
    } catch (error: any) {
      console.error('Error checking job status:', error);
    }
  };

  const downloadPdf = async (): Promise<void> => {
    if (!currentJob) return;
    try {
      const response: AxiosResponse<Blob> = await axios.get(`${API_BASE_URL}/api/jobs/${currentJob}/pdf`, {
        responseType: 'blob'
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `slides_job_${currentJob}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (error: any) {
      alert('Error downloading PDF: ' + error.message);
    }
  };

  const getStudyGuide = async (): Promise<void> => {
    if (!currentJob) return;
    try {
      const response: AxiosResponse<StudyGuideResponse> = await axios.get(`${API_BASE_URL}/api/jobs/${currentJob}/study-guide`);
      const newWindow = window.open();
      if (newWindow) {
        newWindow.document.write(`
          <html>
            <head><title>Study Guide - Job ${currentJob}</title></head>
            <body style="font-family: Arial, sans-serif; padding: 20px; line-height: 1.6;">
              <pre style="white-space: pre-wrap;">${response.data.content}</pre>
            </body>
          </html>
        `);
      }
    } catch (error: any) {
      alert('Error getting study guide: ' + error.message);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-800 mb-2">
            🎬 Slide Extractor
          </h1>
          <p className="text-gray-600 text-lg">
            Extract slides from educational videos with AI-powered analysis
          </p>
        </div>

        {/* API Status */}
        <div className="mb-6">
          <div className={`p-4 rounded-lg ${apiStatus.online ? 'bg-green-100 border-green-300' : 'bg-red-100 border-red-300'} border`}>
            <p className="text-sm font-medium">{apiStatus.message}</p>
          </div>
        </div>

        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Left Column - Input Form */}
          <div className="bg-white rounded-lg shadow-lg p-6">
            <h2 className="text-2xl font-semibold mb-4 flex items-center">
              <Settings className="mr-2" size={24} />
              Extraction Settings
            </h2>

            {/* Video URL Input */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Video URL
              </label>
              <div className="flex gap-2">
                <input
                  type="url"
                  value={videoUrl}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => setVideoUrl(e.target.value)}
                  placeholder="https://www.youtube.com/watch?v=..."
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  disabled={isExtracting || isTestingVideo}
                />
                <button
                  onClick={testVideoAccessibility}
                  disabled={isExtracting || isTestingVideo || !videoUrl.trim()}
                  className="px-4 py-2 bg-gray-600 hover:bg-gray-700 disabled:bg-gray-400 text-white text-sm rounded-md"
                >
                  {isTestingVideo ? 'Testing...' : 'Test Video'}
                </button>
              </div>
              {videoTestResult && (
                <div className={`mt-2 p-2 rounded text-sm ${
                  videoTestResult.startsWith('✅') ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                }`}>
                  {videoTestResult}
                </div>
              )}
            </div>

            {/* Basic Options */}
            <div className="mb-6">
              <h3 className="text-lg font-medium mb-3">Basic Options</h3>
              <div className="space-y-2">
                {Object.entries({
                  adaptive_sampling: 'Adaptive Sampling',
                  extract_content: 'Extract Content',
                  organize_slides: 'Organize Slides',
                  generate_pdf: 'Generate PDF'
                }).map(([key, label]) => (
                  <label key={key} className="flex items-center">
                    <input
                      type="checkbox"
                      checked={extractionOptions[key as keyof ExtractionOptions]}
                      onChange={(e: React.ChangeEvent<HTMLInputElement>) => setExtractionOptions(prev => ({
                        ...prev,
                        [key]: e.target.checked
                      }))}
                      disabled={isExtracting}
                      className="mr-2"
                    />
                    <span className="text-sm">{label}</span>
                  </label>
                ))}
              </div>
            </div>

            {/* AI Features */}
            <div className="mb-6">
              <h3 className="text-lg font-medium mb-3">🤖 AI Features</h3>
              <div className="mb-3">
                <input
                  type="password"
                  value={geminiApiKey}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => setGeminiApiKey(e.target.value)}
                  placeholder="Gemini API Key (optional)"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                  disabled={isExtracting}
                />
              </div>
              <div className="space-y-2">
                {Object.entries({
                  enable_transcription: 'Transcription',
                  enable_ocr_enhancement: 'OCR Enhancement',
                  enable_concept_extraction: 'Concept Extraction',
                  enable_slide_descriptions: 'Slide Descriptions'
                }).map(([key, label]) => (
                  <label key={key} className="flex items-center">
                    <input
                      type="checkbox"
                      checked={extractionOptions[key as keyof ExtractionOptions]}
                      onChange={(e: React.ChangeEvent<HTMLInputElement>) => setExtractionOptions(prev => ({
                        ...prev,
                        [key]: e.target.checked
                      }))}
                      disabled={isExtracting}
                      className="mr-2"
                    />
                    <span className="text-sm">{label}</span>
                  </label>
                ))}
              </div>
            </div>

            {/* Start Button */}
            <button
              onClick={startExtraction}
              disabled={isExtracting || !apiStatus.online}
              className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white font-medium py-3 px-4 rounded-md flex items-center justify-center"
            >
              {isExtracting ? (
                <>
                  <Loader className="animate-spin mr-2" size={20} />
                  Processing...
                </>
              ) : (
                <>
                  <Play className="mr-2" size={20} />
                  Start Extraction
                </>
              )}
            </button>
          </div>

          {/* Right Column - Status and Results */}
          <div className="bg-white rounded-lg shadow-lg p-6">
            <h2 className="text-2xl font-semibold mb-4">
              📊 Status & Results
            </h2>

            {jobStatus ? (
              <div className="space-y-4">
                {/* Job Status */}
                <div className="p-4 bg-gray-50 rounded-lg">
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-medium">Job #{currentJob}</span>
                    <span className={`px-2 py-1 rounded text-sm ${
                      jobStatus.status === 'completed' ? 'bg-green-100 text-green-800' :
                      jobStatus.status === 'failed' ? 'bg-red-100 text-red-800' :
                      'bg-blue-100 text-blue-800'
                    }`}>
                      {jobStatus.status}
                    </span>
                  </div>
                  
                  {/* Progress Bar */}
                  <div className="w-full bg-gray-200 rounded-full h-2 mb-2">
                    <div
                      className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                      style={{ width: `${jobStatus.progress || 0}%` }}
                    ></div>
                  </div>
                  
                  <p className="text-sm text-gray-600">{jobStatus.message}</p>
                  
                  {jobStatus.error && (
                    <p className="text-sm text-red-600 mt-2">Error: {jobStatus.error}</p>
                  )}
                </div>

                {/* Results */}
                {jobStatus.status === 'completed' && (
                  <div className="space-y-3">
                    <div className="flex items-center text-green-600">
                      <CheckCircle className="mr-2" size={20} />
                      <span className="font-medium">Extraction Completed!</span>
                    </div>
                    
                    <div className="grid grid-cols-1 gap-2">
                      <div className="p-3 bg-blue-50 rounded border">
                        <span className="text-sm font-medium">Slides Found: </span>
                        <span className="text-sm">{jobStatus.slides_count || 0}</span>
                      </div>
                      
                      {jobStatus.has_pdf && (
                        <button
                          onClick={downloadPdf}
                          className="flex items-center justify-center p-3 bg-green-50 hover:bg-green-100 border border-green-200 rounded transition-colors"
                        >
                          <Download className="mr-2" size={16} />
                          <span className="text-sm font-medium">Download PDF</span>
                        </button>
                      )}
                      
                      {jobStatus.has_study_guide && (
                        <button
                          onClick={getStudyGuide}
                          className="flex items-center justify-center p-3 bg-purple-50 hover:bg-purple-100 border border-purple-200 rounded transition-colors"
                        >
                          <FileText className="mr-2" size={16} />
                          <span className="text-sm font-medium">View Study Guide</span>
                        </button>
                      )}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-8 text-gray-500">
                <Play size={48} className="mx-auto mb-4 opacity-50" />
                <p>Start an extraction to see progress and results here</p>
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="text-center mt-8 text-gray-500 text-sm">
          <p>Powered by AI • Extract slides from educational videos</p>
        </div>
      </div>
    </div>
  );
};

export default App;
