import React from 'react';
import { FeatureToggleProps } from '../types';

const FeatureToggle: React.FC<FeatureToggleProps> = ({ 
  label, 
  checked, 
  onChange, 
  disabled = false 
}) => {
  return (
    <label className="flex items-center space-x-3 p-2 rounded-lg hover:bg-gray-50 transition-colors">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        disabled={disabled}
        className="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 focus:ring-2 disabled:opacity-50"
      />
      <span className={`text-sm font-medium ${disabled ? 'text-gray-400' : 'text-gray-700'}`}>
        {label}
      </span>
    </label>
  );
};

export default FeatureToggle;
