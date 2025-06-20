import React from 'react';
import { Play, Download, FileText, Settings, CheckCircle, Loader } from 'lucide-react';
import { ExtractionOptionKey } from './types';
import { ProgressBar, StatusIndicator, FeatureToggle } from './components';
import { useExtraction } from './hooks/useExtraction';

const App: React.FC = () => {
  const {
    apiStatus,
    videoUrl,
    extractionOptions,
    geminiApiKey,
    currentJob,
    jobStatus,
    isExtracting,
    setVideoUrl,
    setExtractionOptions,
    setGeminiApiKey,
    startExtraction: startExtractionHook,
    downloadPdf,
    viewStudyGuide,
    refreshApiStatus
  } = useExtraction();

  // Event handlers
  const handleStartExtraction = async (): Promise<void> => {
    try {
      await startExtractionHook();
    } catch (error: any) {
      alert(error.message);
    }
  };

  const handleDownloadPdf = async (): Promise<void> => {
    try {
      await downloadPdf();
    } catch (error: any) {
      alert(error.message);
    }
  };

  const handleViewStudyGuide = async (): Promise<void> => {
    try {
      await viewStudyGuide();
    } catch (error: any) {
      alert(error.message);
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
            <div className="flex justify-between items-center">
              <p className="text-sm font-medium">{apiStatus.message}</p>
              <button
                onClick={refreshApiStatus}
                className="px-3 py-1 text-sm bg-blue-100 hover:bg-blue-200 text-blue-700 rounded-md transition-colors"
              >
                🔄 Refresh
              </button>
            </div>
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
              <input
                type="url"
                value={videoUrl}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setVideoUrl(e.target.value)}
                placeholder="https://www.youtube.com/watch?v=..."
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                disabled={isExtracting}
              />
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
              onClick={handleStartExtraction}
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
                          onClick={handleDownloadPdf}
                          className="flex items-center justify-center p-3 bg-green-50 hover:bg-green-100 border border-green-200 rounded transition-colors"
                        >
                          <Download className="mr-2" size={16} />
                          <span className="text-sm font-medium">Download PDF</span>
                        </button>
                      )}
                      
                      {jobStatus.has_study_guide && (
                        <button
                          onClick={handleViewStudyGuide}
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
