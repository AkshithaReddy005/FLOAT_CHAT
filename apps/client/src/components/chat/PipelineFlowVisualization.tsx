import React, { useState } from 'react';
import { ChevronDown, ChevronRight, Clock, CheckCircle, AlertTriangle, Database, Search, Cpu, BarChart3, Shield } from 'lucide-react';
import type { PipelineFlow } from '../../types';

interface PipelineFlowVisualizationProps {
  pipelineFlow: PipelineFlow;
}

const getStepIcon = (stepName: string) => {
  switch (stepName.toLowerCase()) {
    case 'parameter extraction':
      return <Search className="w-4 h-4" />;
    case 'chromadb vector search':
      return <Database className="w-4 h-4" />;
    case 'sql generation & execution':
      return <Cpu className="w-4 h-4" />;
    case 'ai response generation':
      return <BarChart3 className="w-4 h-4" />;
    case 'consistency validation':
      return <Shield className="w-4 h-4" />;
    default:
      return <CheckCircle className="w-4 h-4" />;
  }
};

const getStatusColor = (status: string) => {
  switch (status.toLowerCase()) {
    case 'success':
      return 'text-green-600 bg-green-50 border-green-200';
    case 'warning':
      return 'text-yellow-600 bg-yellow-50 border-yellow-200';
    case 'error':
      return 'text-red-600 bg-red-50 border-red-200';
    default:
      return 'text-blue-600 bg-blue-50 border-blue-200';
  }
};

const getStatusIcon = (status: string) => {
  switch (status.toLowerCase()) {
    case 'success':
      return <CheckCircle className="w-4 h-4 text-green-600" />;
    case 'warning':
      return <AlertTriangle className="w-4 h-4 text-yellow-600" />;
    case 'error':
      return <AlertTriangle className="w-4 h-4 text-red-600" />;
    default:
      return <CheckCircle className="w-4 h-4 text-blue-600" />;
  }
};

export const PipelineFlowVisualization: React.FC<PipelineFlowVisualizationProps> = ({ pipelineFlow }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [expandedSteps, setExpandedSteps] = useState<Set<string>>(new Set());

  const toggleStepExpansion = (stepName: string) => {
    const newExpanded = new Set(expandedSteps);
    if (newExpanded.has(stepName)) {
      newExpanded.delete(stepName);
    } else {
      newExpanded.add(stepName);
    }
    setExpandedSteps(newExpanded);
  };

  const renderDetailedSection = (title: string, data: any) => {
    if (!data) return null;

    return (
      <div className="mt-3 p-3 bg-gray-50 rounded-lg">
        <h5 className="font-medium text-gray-900 mb-2">{title}</h5>
        <div className="space-y-2 text-sm">
          {Object.entries(data).map(([key, value]) => {
            if (key === 'sample_results' || key === 'sample_documents') {
              return (
                <div key={key}>
                  <span className="font-medium text-gray-700">{key.replace(/_/g, ' ')}:</span>
                  <div className="mt-1 max-h-32 overflow-y-auto">
                    <pre className="text-xs bg-white p-2 rounded border">
                      {JSON.stringify(value, null, 2)}
                    </pre>
                  </div>
                </div>
              );
            }
            if (typeof value === 'object' && value !== null) {
              return (
                <div key={key}>
                  <span className="font-medium text-gray-700">{key.replace(/_/g, ' ')}:</span>
                  <div className="ml-2 mt-1">
                    {Object.entries(value).map(([subKey, subValue]) => (
                      <div key={subKey} className="text-gray-600">
                        <span className="font-medium">{subKey}:</span> {String(subValue)}
                      </div>
                    ))}
                  </div>
                </div>
              );
            }
            return (
              <div key={key} className="text-gray-600">
                <span className="font-medium text-gray-700">{key.replace(/_/g, ' ')}:</span> {String(value)}
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  return (
    <div className="mt-4 border border-gray-200 rounded-lg bg-white">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-4 py-3 flex items-center justify-between text-left hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center space-x-2">
          <Clock className="w-4 h-4 text-blue-600" />
          <span className="font-medium text-gray-900">Pipeline Execution Flow</span>
          <span className="text-sm text-gray-500">({pipelineFlow.total_duration})</span>
        </div>
        {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
      </button>

      {isExpanded && (
        <div className="px-4 pb-4 border-t border-gray-100">
          <div className="space-y-3 mt-3">
            {pipelineFlow.steps.map((step, index) => (
              <div key={index} className="border border-gray-200 rounded-lg">
                <button
                  onClick={() => toggleStepExpansion(step.step)}
                  className={`w-full px-3 py-2 flex items-center justify-between text-left hover:bg-gray-50 transition-colors rounded-lg ${getStatusColor(step.status)}`}
                >
                  <div className="flex items-center space-x-2">
                    {getStepIcon(step.step)}
                    <span className="font-medium">{step.step}</span>
                    <span className="text-xs">({step.duration})</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    {getStatusIcon(step.status)}
                    {expandedSteps.has(step.step) ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
                  </div>
                </button>

                {expandedSteps.has(step.step) && (
                  <div className="px-3 pb-3 border-t border-gray-200 bg-white">
                    <p className="text-sm text-gray-600 mt-2">{step.details}</p>
                    
                    {step.step === 'Parameter Extraction' && renderDetailedSection('Extraction Details', pipelineFlow.parameter_extraction)}
                    {step.step === 'SQL Generation & Execution' && renderDetailedSection('SQL Details', pipelineFlow.sql_generation)}
                    {step.step === 'ChromaDB Vector Search' && renderDetailedSection('Vector Search Details', pipelineFlow.chroma_search)}
                    {step.step === 'AI Response Generation' && renderDetailedSection('AI Response Details', pipelineFlow.api_response)}
                    {step.step === 'Consistency Validation' && renderDetailedSection('Validation Details', pipelineFlow.consistency_validation)}
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Pipeline Summary */}
          <div className="mt-4 p-3 bg-blue-50 rounded-lg border border-blue-200">
            <h4 className="font-medium text-blue-900 mb-2">Pipeline Summary</h4>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="font-medium text-blue-800">Total Duration:</span>
                <span className="ml-2 text-blue-700">{pipelineFlow.total_duration}</span>
              </div>
              <div>
                <span className="font-medium text-blue-800">Steps Completed:</span>
                <span className="ml-2 text-blue-700">{pipelineFlow.steps.length}</span>
              </div>
              {pipelineFlow.sql_generation && (
                <div>
                  <span className="font-medium text-blue-800">Records Found:</span>
                  <span className="ml-2 text-blue-700">{pipelineFlow.sql_generation.records_returned}</span>
                </div>
              )}
              {pipelineFlow.chroma_search && (
                <div>
                  <span className="font-medium text-blue-800">Documents Found:</span>
                  <span className="ml-2 text-blue-700">{pipelineFlow.chroma_search.documents_found}</span>
                </div>
              )}
              {pipelineFlow.consistency_validation && (
                <div className="col-span-2">
                  <span className="font-medium text-blue-800">Consistency:</span>
                  <span className={`ml-2 ${pipelineFlow.consistency_validation.is_consistent ? 'text-green-700' : 'text-red-700'}`}>
                    {pipelineFlow.consistency_validation.is_consistent ? '✅ Consistent' : `❌ ${pipelineFlow.consistency_validation.violations_count} violations`}
                  </span>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
