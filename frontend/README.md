# 🎨 Slide Extractor Frontend (TypeScript)

A modern React TypeScript frontend for the Slide Extractor API with real-time progress monitoring and file downloads.

## ✨ Features

- **🔧 TypeScript**: Full type safety and better development experience
- **⚡ React 18**: Modern React with hooks and functional components
- **🎨 Tailwind CSS**: Utility-first CSS framework for rapid styling
- **📊 Real-time Updates**: Live progress monitoring and status updates
- **📱 Responsive Design**: Mobile-friendly interface
- **🔄 Custom Hooks**: Reusable logic with `useExtraction` hook
- **🧩 Component Architecture**: Modular, reusable components
- **🛡️ Error Handling**: Comprehensive error handling and user feedback

## 🏗️ Architecture

```
src/
├── components/          # Reusable UI components
│   ├── ProgressBar.tsx  # Progress visualization
│   ├── StatusIndicator.tsx # Status display
│   ├── FeatureToggle.tsx   # Checkbox components
│   └── index.ts         # Component exports
├── hooks/               # Custom React hooks
│   └── useExtraction.ts # Main extraction logic
├── types/               # TypeScript type definitions
│   └── index.ts         # All interface definitions
├── utils/               # Utility functions
│   └── api.ts           # API client and functions
├── App.tsx              # Main application component
├── index.tsx            # Application entry point
└── index.css            # Global styles
```

## 🚀 Quick Start

### Prerequisites
- Node.js 16+
- npm or yarn

### Installation
```bash
# Install dependencies
npm install

# Start development server
npm start

# Build for production
npm run build
```

### Environment Variables
Create a `.env` file:
```env
REACT_APP_API_URL=https://your-backend-url.onrender.com
```

## 🔧 TypeScript Features

### Type Safety
- **API Responses**: Fully typed API responses and requests
- **Component Props**: Strict typing for all component props
- **Event Handlers**: Type-safe event handling
- **State Management**: Typed state with proper interfaces

### Custom Types
```typescript
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
  status: 'initializing' | 'processing' | 'completed' | 'failed';
  progress: number;
  message: string;
  error?: string;
  slides_count?: number;
  has_pdf?: boolean;
  has_study_guide?: boolean;
}
```

## 🧩 Components

### ProgressBar
```typescript
interface ProgressBarProps {
  progress: number;
  status: string;
  message?: string;
}
```

### StatusIndicator
```typescript
interface StatusIndicatorProps {
  status: JobStatus['status'];
  message: string;
}
```

### FeatureToggle
```typescript
interface FeatureToggleProps {
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
}
```

## 🪝 Custom Hooks

### useExtraction
Manages all extraction-related state and logic:

```typescript
const {
  apiStatus,
  videoUrl,
  extractionOptions,
  currentJob,
  jobStatus,
  isExtracting,
  setVideoUrl,
  setExtractionOptions,
  startExtraction,
  downloadPdf,
  viewStudyGuide,
  refreshApiStatus
} = useExtraction();
```

## 🌐 API Integration

### Typed API Client
```typescript
// API functions with full type safety
export const startExtraction = async (request: ExtractionRequest): Promise<ExtractResponse>
export const getJobStatus = async (jobId: string): Promise<JobStatus>
export const downloadJobPdf = async (jobId: string): Promise<Blob>
```

### Error Handling
```typescript
interface ApiError {
  error: string;
  message?: string;
  status_code?: number;
}
```

## 🎨 Styling

### Tailwind CSS Classes
- **Layout**: Grid, flexbox, responsive design
- **Colors**: Semantic color system
- **Animations**: Smooth transitions and loading states
- **Components**: Consistent button and form styling

### Custom CSS
```css
/* Loading animation */
@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.animate-spin {
  animation: spin 1s linear infinite;
}
```

## 📱 Responsive Design

- **Mobile First**: Optimized for mobile devices
- **Breakpoints**: Responsive grid layout
- **Touch Friendly**: Large touch targets
- **Accessibility**: ARIA labels and keyboard navigation

## 🔄 State Management

### Local State with Hooks
- **useState**: Component-level state
- **useEffect**: Side effects and lifecycle
- **useCallback**: Memoized functions
- **Custom Hooks**: Shared logic

### State Flow
```
User Input → useExtraction Hook → API Calls → State Updates → UI Re-render
```

## 🛠️ Development

### TypeScript Configuration
```json
{
  "compilerOptions": {
    "target": "es5",
    "strict": true,
    "jsx": "react-jsx",
    "moduleResolution": "node"
  }
}
```

### Build Process
1. **TypeScript Compilation**: TSC checks types
2. **React Build**: Create React App builds optimized bundle
3. **Tailwind Processing**: CSS optimization
4. **Asset Optimization**: Images and static files

## 🚀 Deployment

### Build for Production
```bash
npm run build
```

### Deploy to Netlify
```bash
# Build command
npm run build

# Publish directory
build

# Environment variables
REACT_APP_API_URL=https://your-backend-url.onrender.com
```

## 🧪 Testing

### Type Checking
```bash
# Check types
npx tsc --noEmit

# Watch mode
npx tsc --noEmit --watch
```

### Component Testing
```typescript
import { render, screen } from '@testing-library/react';
import App from './App';

test('renders slide extractor interface', () => {
  render(<App />);
  const heading = screen.getByText(/slide extractor/i);
  expect(heading).toBeInTheDocument();
});
```

## 📊 Performance

### Optimization Features
- **Code Splitting**: Lazy loading components
- **Memoization**: useCallback and useMemo
- **Bundle Analysis**: Webpack bundle analyzer
- **Tree Shaking**: Dead code elimination

### Bundle Size
- **Gzipped**: ~50KB (estimated)
- **Dependencies**: React, Axios, Lucide React, Tailwind CSS

## 🔧 Configuration

### Package.json Scripts
```json
{
  "scripts": {
    "start": "react-scripts start",
    "build": "react-scripts build",
    "test": "react-scripts test",
    "eject": "react-scripts eject",
    "type-check": "tsc --noEmit"
  }
}
```

## 🤝 Contributing

1. **Type Safety**: Ensure all new code is properly typed
2. **Component Structure**: Follow established patterns
3. **Error Handling**: Add proper error boundaries
4. **Testing**: Write tests for new components
5. **Documentation**: Update README for new features

## 📄 License

MIT License - see LICENSE file for details.

---

**Built with ❤️ using React, TypeScript, and Tailwind CSS**
