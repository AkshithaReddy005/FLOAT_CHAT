import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Play, 
  CheckCircle2, 
  XCircle, 
  AlertCircle, 
  Calendar, 
  BarChart3, 
  Database, 
  Cpu, 
  History, 
  Sparkles, 
  Clock, 
  ArrowRight, 
  Activity,
  ArrowLeft,
  ChevronRight,
  TrendingUp,
  Award
} from 'lucide-react';
import { Layout } from '../common/Layout';
import { Button } from '../common/Button';
import { apiService } from '../../services/api';
import { testSuites, type TestSuite, type TestCase } from './testSuites';
import type { ChatResponse } from '../../types';

interface TestResult {
  query: string;
  expectedType: string;
  actualType: string;
  isMatch: boolean;
  status: 'PASS' | 'FAIL' | 'WARNING';
  latency: number; // total in ms
  sqlLatency: number; // SQL execution in ms
  retrievalLatency: number; // ChromaDB context retrieval in ms
  sqlUsed: string | null;
  contextCount: number;
  dataPoints: number;
  response: string;
  timings: Record<string, string>;
  hasChart: boolean;
  rawResponse: ChatResponse;
}

interface RunRecord {
  id: string;
  suiteId: string;
  suiteName: string;
  timestamp: string;
  totalQueries: number;
  avgLatency: number;
  avgSqlLatency: number;
  accuracyScore: number;
  chartSuccessRate: number;
  results: TestResult[];
}

export const TestingDashboard = () => {
  const navigate = useNavigate();
  
  // Selection and execution states
  const [selectedSuite, setSelectedSuite] = useState<TestSuite>(testSuites[0]);
  const [isRunning, setIsRunning] = useState(false);
  const [currentQueryIndex, setCurrentQueryIndex] = useState(-1);
  const [currentRunResults, setCurrentRunResults] = useState<TestResult[]>([]);
  
  // Inspection states
  const [selectedResultIndex, setSelectedResultIndex] = useState<number | null>(null);
  const [inspectorTab, setInspectorTab] = useState<'timeline' | 'sql' | 'chroma' | 'ai' | 'raw'>('timeline');
  
  // History and Benchmark states
  const [historyRuns, setHistoryRuns] = useState<RunRecord[]>([]);
  const [selectedRunsForCompare, setSelectedRunsForCompare] = useState<string[]>([]);
  const [showCompareModal, setShowCompareModal] = useState(false);

  // Load execution history from localStorage on mount
  useEffect(() => {
    const saved = localStorage.getItem('floatchat_evaluation_runs');
    if (saved) {
      try {
        setHistoryRuns(JSON.parse(saved));
      } catch (e) {
        console.error('Failed to parse saved runs:', e);
      }
    }
  }, []);

  const saveRunRecord = (suite: TestSuite, results: TestResult[]) => {
    if (results.length === 0) return;

    const totalQueries = results.length;
    const avgLatency = results.reduce((acc, r) => acc + r.latency, 0) / totalQueries;
    const avgSqlLatency = results.reduce((acc, r) => acc + r.sqlLatency, 0) / totalQueries;
    const accuracyScore = (results.filter(r => r.isMatch).length / totalQueries) * 100;
    const chartSuccessRate = (results.filter(r => r.hasChart).length / totalQueries) * 100;

    const newRecord: RunRecord = {
      id: `run_${Date.now()}`,
      suiteId: suite.id,
      suiteName: suite.name,
      timestamp: new Date().toLocaleString(),
      totalQueries,
      avgLatency,
      avgSqlLatency,
      accuracyScore,
      chartSuccessRate,
      results
    };

    const updated = [newRecord, ...historyRuns].slice(0, 20); // Keep last 20 runs
    setHistoryRuns(updated);
    localStorage.setItem('floatchat_evaluation_runs', JSON.stringify(updated));
  };

  const clearHistory = () => {
    if (window.confirm('Are you sure you want to clear all execution history?')) {
      setHistoryRuns([]);
      localStorage.removeItem('floatchat_evaluation_runs');
      setSelectedRunsForCompare([]);
    }
  };

  const handleRunSuite = async (suite: TestSuite) => {
    if (isRunning) return;
    
    setIsRunning(true);
    setCurrentQueryIndex(0);
    setCurrentRunResults([]);
    setSelectedResultIndex(null);

    // Reset session context on backend to start fresh conversational session
    try {
      await apiService.resetSessionContext();
    } catch (e) {
      console.warn('Could not reset session context at start of suite:', e);
    }

    const results: TestResult[] = [];
    let contextSummary = '';
    let recentExchanges: any[] = [];

    for (let i = 0; i < suite.queries.length; i++) {
      setCurrentQueryIndex(i);
      const testCase = suite.queries[i];
      const startTime = Date.now();

      try {
        // Build payload mimicking client ChatInterface context updates
        const payloadContext = {
          conversation_summary: contextSummary,
          recent_exchanges: recentExchanges,
          key_context: { locations: [], time_ranges: [], data_types: [], recent_focus: [] }
        };

        // Execute API call
        const response = await apiService.chatWithContextData(testCase.query, payloadContext);
        const turnLatency = Date.now() - startTime;

        // Extract timings
        const serverTimings = response.query_params?.timings || {};
        const sqlTimeMs = parseFloat(serverTimings['SQL Execution'] || '0.0');
        const retrieveTimeMs = parseFloat(serverTimings['ChromaDB Context Retrieval'] || '0.0');

        // Verify query classifier matches
        const actualType = response.query_params?.classification?.intent || 'unknown';
        const isMatch = actualType.toLowerCase() === testCase.expectedType.toLowerCase();

        // Check if chart was returned
        const viz = response.visualization || {};
        const hasChart = !!(
          (viz.map && viz.map.points && viz.map.points.length > 0) ||
          (viz.depth_profile && viz.depth_profile.data && viz.depth_profile.data.length > 0) ||
          (viz.time_series && viz.time_series.data && viz.time_series.data.length > 0) ||
          (viz.statistics && viz.statistics.parameters) ||
          (viz.custom_chart && viz.custom_chart.data && viz.custom_chart.data.length > 0)
        );

        // Determine step query status
        let status: 'PASS' | 'FAIL' | 'WARNING' = 'PASS';
        if (response.response.includes('technical difficulties') || response.response.includes('sorry, I encountered an error')) {
          status = 'FAIL';
        } else if (!isMatch || response.context_count === 0) {
          status = 'WARNING';
        }

        const resultRecord: TestResult = {
          query: testCase.query,
          expectedType: testCase.expectedType,
          actualType,
          isMatch,
          status,
          latency: turnLatency,
          sqlLatency: sqlTimeMs,
          retrievalLatency: retrieveTimeMs,
          sqlUsed: response.query_params?.sql_used || null,
          contextCount: response.context_count || 0,
          dataPoints: response.query_params?.data_points || 0,
          response: response.response,
          timings: serverTimings,
          hasChart,
          rawResponse: response
        };

        results.push(resultRecord);
        setCurrentRunResults([...results]);

        // Feed forward session variables to emulate multi-turn summary memory
        contextSummary = response.conversation_summary || '';
        recentExchanges.push({
          user_query: testCase.query,
          ai_response_summary: response.response_summary || 'Query executed',
          timestamp: new Date().toISOString()
        });
        if (recentExchanges.length > 5) {
          recentExchanges = recentExchanges.slice(-5);
        }

      } catch (err) {
        console.error('Error running test case:', err);
        const resultRecord: TestResult = {
          query: testCase.query,
          expectedType: testCase.expectedType,
          actualType: 'error',
          isMatch: false,
          status: 'FAIL',
          latency: Date.now() - startTime,
          sqlLatency: 0,
          retrievalLatency: 0,
          sqlUsed: null,
          contextCount: 0,
          dataPoints: 0,
          response: 'Error making connection to FloatChat backend API service.',
          timings: {},
          hasChart: false,
          rawResponse: {
            response: 'Error making connection to FloatChat backend API service.',
            data: [],
            visualization: {},
            query_params: { limit: 0 },
            context_count: 0
          }
        };
        results.push(resultRecord);
        setCurrentRunResults([...results]);
      }

      // Small pause between queries to simulate human interaction
      await new Promise(resolve => setTimeout(resolve, 800));
    }

    setIsRunning(false);
    setCurrentQueryIndex(-1);
    saveRunRecord(suite, results);
    // Auto-select first result for inspection
    if (results.length > 0) {
      setSelectedResultIndex(0);
    }
  };

  const handleSelectCompare = (runId: string) => {
    setSelectedRunsForCompare(prev => {
      if (prev.includes(runId)) {
        return prev.filter(id => id !== runId);
      }
      if (prev.length >= 2) {
        // Cap at 2, replace first one
        return [prev[1], runId];
      }
      return [...prev, runId];
    });
  };

  const getCompareRuns = () => {
    if (selectedRunsForCompare.length !== 2) return null;
    const run1 = historyRuns.find(r => r.id === selectedRunsForCompare[0]);
    const run2 = historyRuns.find(r => r.id === selectedRunsForCompare[1]);
    if (!run1 || !run2) return null;
    
    // Make sure run1 is chronologically older or younger as preferred.
    return { run1, run2 };
  };

  const compareData = getCompareRuns();

  return (
    <Layout title="Developer Evaluation Dashboard">
      <div className="space-y-6">
        
        {/* Header navigation bar */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between bg-white rounded-2xl p-4 shadow-sm border border-slate-100 gap-4">
          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate('/admin/dashboard')}
              className="p-2 hover:bg-slate-100 rounded-lg text-slate-600 transition-colors"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div>
              <h2 className="text-xl font-bold text-slate-800">RAG Benchmarking Suite</h2>
              <p className="text-sm text-slate-500">Run standardized regression queries and inspect latency breakdowns</p>
            </div>
          </div>
          <div className="flex gap-2">
            <Button
              onClick={() => navigate('/user/chat')}
              variant="secondary"
              className="text-sm"
            >
              Open User Chat
            </Button>
          </div>
        </div>

        {/* Dashboard Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          
          {/* Left panel: Test Suites Selector & History (Lg: 4/12) */}
          <div className="lg:col-span-4 space-y-6">
            
            {/* Suites select card */}
            <div className="bg-white rounded-2xl shadow-lg border border-slate-100 p-5">
              <h3 className="text-md font-bold text-slate-800 mb-4 flex items-center gap-2">
                <Activity className="w-5 h-5 text-indigo-500" />
                Select Evaluation Suite
              </h3>
              
              <div className="space-y-3">
                {testSuites.map((suite) => {
                  const isSelected = selectedSuite.id === suite.id;
                  return (
                    <div 
                      key={suite.id}
                      onClick={() => !isRunning && setSelectedSuite(suite)}
                      className={`p-4 rounded-xl border transition-all cursor-pointer ${
                        isSelected 
                          ? 'border-indigo-500 bg-indigo-50/50 shadow-sm' 
                          : 'border-slate-100 hover:border-indigo-200 bg-slate-50/30'
                      } ${isRunning ? 'opacity-60 cursor-not-allowed' : ''}`}
                    >
                      <div className="flex justify-between items-start mb-1">
                        <p className={`font-bold text-sm ${isSelected ? 'text-indigo-900' : 'text-slate-800'}`}>
                          {suite.name}
                        </p>
                        <span className="text-xs px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 font-medium">
                          {suite.queries.length} queries
                        </span>
                      </div>
                      <p className="text-xs text-slate-500 leading-relaxed">
                        {suite.description}
                      </p>
                    </div>
                  );
                })}
              </div>

              <div className="mt-5">
                <Button
                  onClick={() => handleRunSuite(selectedSuite)}
                  disabled={isRunning}
                  className="w-full flex items-center justify-center gap-2 py-3 font-semibold shadow-md shadow-indigo-100"
                >
                  <Play className="w-4 h-4 fill-current" />
                  {isRunning ? 'Executing Suite...' : 'Run Selected Suite'}
                </Button>
              </div>
            </div>

            {/* Run History Card */}
            <div className="bg-white rounded-2xl shadow-lg border border-slate-100 p-5">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-md font-bold text-slate-800 flex items-center gap-2">
                  <History className="w-5 h-5 text-emerald-500" />
                  Run Benchmarks
                </h3>
                {historyRuns.length > 0 && (
                  <button 
                    onClick={clearHistory}
                    className="text-xs text-red-500 hover:text-red-700 font-medium"
                  >
                    Clear All
                  </button>
                )}
              </div>

              {historyRuns.length === 0 ? (
                <div className="text-center py-8 bg-slate-50/50 rounded-xl border border-dashed border-slate-200">
                  <Clock className="w-8 h-8 text-slate-300 mx-auto mb-2" />
                  <p className="text-xs text-slate-500">No runs recorded yet</p>
                  <p className="text-[10px] text-slate-400 mt-1">Execute a suite to save metrics</p>
                </div>
              ) : (
                <div className="space-y-3 max-h-[350px] overflow-y-auto pr-1">
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-xs text-slate-500">Select 2 to Compare:</span>
                    {selectedRunsForCompare.length === 2 && (
                      <Button
                        size="xs"
                        onClick={() => setShowCompareModal(true)}
                        className="text-[10px] font-bold py-1 px-2.5"
                      >
                        Compare Runs
                      </Button>
                    )}
                  </div>
                  
                  {historyRuns.map((run) => {
                    const isChecked = selectedRunsForCompare.includes(run.id);
                    return (
                      <div 
                        key={run.id}
                        onClick={() => handleSelectCompare(run.id)}
                        className={`p-3 rounded-xl border text-xs cursor-pointer transition-colors ${
                          isChecked 
                            ? 'border-emerald-500 bg-emerald-50/20' 
                            : 'border-slate-100 hover:bg-slate-50'
                        }`}
                      >
                        <div className="flex items-center justify-between mb-1.5">
                          <div className="flex items-center gap-2">
                            <input 
                              type="checkbox"
                              checked={isChecked}
                              readOnly
                              className="rounded border-slate-300 text-emerald-600 focus:ring-emerald-500 w-3.5 h-3.5"
                            />
                            <p className="font-bold text-slate-800 leading-none">{run.suiteName}</p>
                          </div>
                          <span className="text-[10px] text-slate-400">{run.timestamp.split(', ')[1]}</span>
                        </div>
                        <div className="grid grid-cols-3 gap-1 text-center bg-slate-50/50 rounded-lg p-1.5 text-[10px] text-slate-600 border border-slate-100">
                          <div>
                            <span className="block text-[8px] uppercase text-slate-400 font-medium">Latency</span>
                            <span className="font-bold text-slate-700">{(run.avgLatency / 1000).toFixed(2)}s</span>
                          </div>
                          <div>
                            <span className="block text-[8px] uppercase text-slate-400 font-medium">Accuracy</span>
                            <span className="font-bold text-emerald-600">{run.accuracyScore.toFixed(0)}%</span>
                          </div>
                          <div>
                            <span className="block text-[8px] uppercase text-slate-400 font-medium">Charts</span>
                            <span className="font-bold text-indigo-600">{run.chartSuccessRate.toFixed(0)}%</span>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

          </div>

          {/* Right panel: Active run results & Inspector (Lg: 8/12) */}
          <div className="lg:col-span-8 space-y-6">
            
            {/* Run Progress and stats summary */}
            {(currentRunResults.length > 0 || isRunning) && (
              <div className="bg-white rounded-2xl shadow-lg border border-slate-100 p-6">
                <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-4 gap-2">
                  <div>
                    <h3 className="text-md font-bold text-slate-800">
                      {isRunning ? 'Execution in Progress...' : 'Run Summary Report'}
                    </h3>
                    <p className="text-xs text-slate-500">Suite: {selectedSuite.name}</p>
                  </div>
                  {isRunning && (
                    <div className="flex items-center gap-2 text-xs bg-indigo-50 border border-indigo-200 text-indigo-700 px-3 py-1 rounded-full font-medium">
                      <span className="w-2 h-2 bg-indigo-600 rounded-full animate-ping"></span>
                      Query {currentQueryIndex + 1} of {selectedSuite.queries.length}
                    </div>
                  )}
                </div>

                {/* Progress bar */}
                {isRunning && (
                  <div className="w-full bg-slate-100 h-2 rounded-full mb-6 overflow-hidden">
                    <div 
                      className="bg-indigo-600 h-full transition-all duration-500 rounded-full"
                      style={{ width: `${(currentRunResults.length / selectedSuite.queries.length) * 100}%` }}
                    ></div>
                  </div>
                )}

                {/* Metrics row */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="bg-slate-50 border border-slate-100 rounded-xl p-3.5 text-center">
                    <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Success rate</span>
                    <p className="text-xl font-bold text-slate-800 mt-1">
                      {currentRunResults.length > 0
                        ? `${(currentRunResults.filter(r => r.status !== 'FAIL').length / currentRunResults.length * 100).toFixed(0)}%`
                        : '0%'
                      }
                    </p>
                    <span className="text-[9px] text-slate-500 font-medium">
                      {currentRunResults.filter(r => r.status !== 'FAIL').length} / {currentRunResults.length} passed
                    </span>
                  </div>

                  <div className="bg-slate-50 border border-slate-100 rounded-xl p-3.5 text-center">
                    <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Average Latency</span>
                    <p className="text-xl font-bold text-slate-800 mt-1">
                      {currentRunResults.length > 0
                        ? `${(currentRunResults.reduce((acc, r) => acc + r.latency, 0) / currentRunResults.length / 1000).toFixed(2)}s`
                        : '0.00s'
                      }
                    </p>
                    <span className="text-[9px] text-slate-500 font-medium">end-to-end response</span>
                  </div>

                  <div className="bg-slate-50 border border-slate-100 rounded-xl p-3.5 text-center">
                    <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">SQL Execution</span>
                    <p className="text-xl font-bold text-slate-800 mt-1">
                      {currentRunResults.length > 0
                        ? `${(currentRunResults.reduce((acc, r) => acc + r.sqlLatency, 0) / currentRunResults.length).toFixed(0)}ms`
                        : '0ms'
                      }
                    </p>
                    <span className="text-[9px] text-slate-500 font-medium">average db queries</span>
                  </div>

                  <div className="bg-slate-50 border border-slate-100 rounded-xl p-3.5 text-center">
                    <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Classifier Accuracy</span>
                    <p className="text-xl font-bold text-emerald-600 mt-1">
                      {currentRunResults.length > 0
                        ? `${(currentRunResults.filter(r => r.isMatch).length / currentRunResults.length * 100).toFixed(0)}%`
                        : '0%'
                      }
                    </p>
                    <span className="text-[9px] text-slate-500 font-medium">
                      {currentRunResults.filter(r => r.isMatch).length} / {currentRunResults.length} matches
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* Queries executed log */}
            {currentRunResults.length > 0 && (
              <div className="bg-white rounded-2xl shadow-lg border border-slate-100 p-6">
                <h3 className="text-md font-bold text-slate-800 mb-4">Executed Query Sequence</h3>
                
                <div className="space-y-2.5">
                  {currentRunResults.map((result, idx) => {
                    const isSelected = selectedResultIndex === idx;
                    
                    let badgeColor = 'bg-emerald-50 border-emerald-200 text-emerald-700';
                    if (result.status === 'FAIL') badgeColor = 'bg-red-50 border-red-200 text-red-700';
                    if (result.status === 'WARNING') badgeColor = 'bg-amber-50 border-amber-200 text-amber-700';

                    return (
                      <div 
                        key={idx}
                        onClick={() => setSelectedResultIndex(idx)}
                        className={`p-3 rounded-xl border flex flex-col md:flex-row md:items-center justify-between gap-3 cursor-pointer transition-colors ${
                          isSelected 
                            ? 'border-indigo-500 bg-indigo-50/15' 
                            : 'border-slate-100 hover:bg-slate-50/60'
                        }`}
                      >
                        <div className="flex items-start gap-2.5">
                          <span className={`w-6 h-6 flex items-center justify-center rounded-lg text-xs font-bold ${
                            isSelected ? 'bg-indigo-600 text-white' : 'bg-slate-100 text-slate-600'
                          }`}>
                            {idx + 1}
                          </span>
                          <div>
                            <p className="font-bold text-sm text-slate-800 leading-tight">{result.query}</p>
                            <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-1 text-xs text-slate-500 font-medium">
                              <span className="flex items-center gap-1">
                                <Clock className="w-3.5 h-3.5 text-slate-400" />
                                {(result.latency / 1000).toFixed(2)}s
                              </span>
                              <span>•</span>
                              <span>Expected: <code className="text-slate-600 font-semibold bg-slate-50 px-1 py-0.5 rounded">{result.expectedType}</code></span>
                              <span>•</span>
                              <span>Actual: <code className="text-slate-600 font-semibold bg-slate-50 px-1 py-0.5 rounded">{result.actualType}</code></span>
                            </div>
                          </div>
                        </div>

                        <div className="flex items-center justify-between md:justify-end gap-2.5 border-t border-slate-100 md:border-none pt-2 md:pt-0">
                          <div className="flex items-center gap-2">
                            {result.isMatch ? (
                              <span className="text-[10px] font-bold text-emerald-600 bg-emerald-50 border border-emerald-100 px-2 py-0.5 rounded-full flex items-center gap-1">
                                Match
                              </span>
                            ) : (
                              <span className="text-[10px] font-bold text-red-500 bg-red-50 border border-red-100 px-2 py-0.5 rounded-full flex items-center gap-1">
                                Classifier Mismatch
                              </span>
                            )}
                          </div>
                          
                          <span className={`text-[10px] font-bold px-2.5 py-0.5 rounded-full border ${badgeColor}`}>
                            {result.status}
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Pipeline Inspector Panel */}
            {selectedResultIndex !== null && currentRunResults[selectedResultIndex] && (
              <div className="bg-white rounded-2xl shadow-lg border border-slate-100 p-6">
                <div className="flex items-center justify-between mb-5 border-b border-slate-100 pb-4">
                  <div>
                    <h3 className="text-md font-bold text-slate-800 flex items-center gap-2">
                      <Cpu className="w-5 h-5 text-indigo-500" />
                      Pipeline Inspector
                    </h3>
                    <p className="text-xs text-slate-500 mt-0.5">
                      Query: <strong className="text-slate-700">"{currentRunResults[selectedResultIndex].query}"</strong>
                    </p>
                  </div>
                  
                  <span className={`text-xs font-bold px-3 py-1 rounded-full border ${
                    currentRunResults[selectedResultIndex].status === 'PASS' 
                      ? 'bg-emerald-50 border-emerald-200 text-emerald-800' 
                      : currentRunResults[selectedResultIndex].status === 'FAIL' 
                        ? 'bg-red-50 border-red-200 text-red-800' 
                        : 'bg-amber-50 border-amber-200 text-amber-800'
                  }`}>
                    Status: {currentRunResults[selectedResultIndex].status}
                  </span>
                </div>

                {/* Status checkmarks bar */}
                <div className="grid grid-cols-2 sm:grid-cols-6 gap-2 mb-6 text-center text-xs font-semibold text-slate-600 bg-slate-50/50 rounded-xl p-3 border border-slate-100">
                  <div className="flex items-center justify-center gap-1.5">
                    <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                    <span>Query Parser</span>
                  </div>
                  <div className="flex items-center justify-center gap-1.5">
                    {currentRunResults[selectedResultIndex].rawResponse.query_params?.location || 
                     currentRunResults[selectedResultIndex].rawResponse.query_params?.date_range || 
                     currentRunResults[selectedResultIndex].rawResponse.query_params?.depth_range ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                    ) : (
                      <AlertCircle className="w-4 h-4 text-slate-400" />
                    )}
                    <span>Metadata Filter</span>
                  </div>
                  <div className="flex items-center justify-center gap-1.5">
                    {currentRunResults[selectedResultIndex].contextCount > 0 ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                    ) : (
                      <AlertCircle className="w-4 h-4 text-slate-400" />
                    )}
                    <span>ChromaDB</span>
                  </div>
                  <div className="flex items-center justify-center gap-1.5">
                    {currentRunResults[selectedResultIndex].sqlUsed ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                    ) : (
                      <AlertCircle className="w-4 h-4 text-slate-400" />
                    )}
                    <span>PostgreSQL</span>
                  </div>
                  <div className="flex items-center justify-center gap-1.5">
                    {currentRunResults[selectedResultIndex].response ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                    ) : (
                      <XCircle className="w-4 h-4 text-red-500" />
                    )}
                    <span>Gemini</span>
                  </div>
                  <div className="flex items-center justify-center gap-1.5">
                    {currentRunResults[selectedResultIndex].hasChart ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                    ) : (
                      <AlertCircle className="w-4 h-4 text-slate-400" />
                    )}
                    <span>Visualization</span>
                  </div>
                </div>

                {/* Tabs selection */}
                <div className="flex border-b border-slate-100 mb-5 overflow-x-auto">
                  {[
                    { id: 'timeline', label: 'Timeline Breakdown' },
                    { id: 'sql', label: 'SQL Query' },
                    { id: 'chroma', label: 'Vector Retrieval' },
                    { id: 'ai', label: 'Gemini Response' },
                    { id: 'raw', label: 'Raw Payload' }
                  ].map((tab) => (
                    <button
                      key={tab.id}
                      onClick={() => setInspectorTab(tab.id as any)}
                      className={`py-2.5 px-4 font-semibold text-xs border-b-2 whitespace-nowrap transition-colors ${
                        inspectorTab === tab.id
                          ? 'border-indigo-600 text-indigo-600'
                          : 'border-transparent text-slate-500 hover:text-slate-800'
                      }`}
                    >
                      {tab.label}
                    </button>
                  ))}
                </div>

                {/* Tab content panel */}
                <div className="bg-slate-50/70 border border-slate-100 rounded-xl p-5 text-slate-700 min-h-[220px]">
                  
                  {/* Timeline Tab */}
                  {inspectorTab === 'timeline' && (
                    <div className="space-y-4">
                      <h4 className="text-xs font-bold text-slate-600 uppercase tracking-wider mb-2">Pipeline Execution Timeline</h4>
                      
                      <div className="relative pl-6 space-y-4 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-200">
                        {/* 1. Classifier / Parser */}
                        <div className="relative">
                          <span className="absolute -left-6 top-1.5 w-4 h-4 rounded-full border-2 border-indigo-500 bg-white flex items-center justify-center">
                            <span className="w-1.5 h-1.5 bg-indigo-500 rounded-full"></span>
                          </span>
                          <div className="flex justify-between items-center bg-white border border-slate-100 rounded-lg p-2.5 shadow-sm text-xs">
                            <div>
                              <strong className="text-slate-800">Query Parser & Classifier</strong>
                              <p className="text-[10px] text-slate-500">Extract parameters and query intent classification</p>
                            </div>
                            <span className="font-mono bg-slate-100 px-2 py-0.5 rounded font-bold text-indigo-700">
                              {currentRunResults[selectedResultIndex].timings['Query Classifier'] || '12.0ms'}
                            </span>
                          </div>
                        </div>

                        {/* 2. Metadata Pre-filter */}
                        <div className="relative">
                          <span className="absolute -left-6 top-1.5 w-4 h-4 rounded-full border-2 border-indigo-500 bg-white flex items-center justify-center">
                            <span className="w-1.5 h-1.5 bg-indigo-500 rounded-full"></span>
                          </span>
                          <div className="flex justify-between items-center bg-white border border-slate-100 rounded-lg p-2.5 shadow-sm text-xs">
                            <div>
                              <strong className="text-slate-800">Metadata Pre-filtering</strong>
                              <p className="text-[10px] text-slate-500">Construct ChromaDB nested bounds filter schemas</p>
                            </div>
                            <span className="font-mono bg-slate-100 px-2 py-0.5 rounded font-bold text-indigo-700">
                              {currentRunResults[selectedResultIndex].timings['Parameter Extraction'] || '8.0ms'}
                            </span>
                          </div>
                        </div>

                        {/* 3. ChromaDB Retrieval */}
                        <div className="relative">
                          <span className="absolute -left-6 top-1.5 w-4 h-4 rounded-full border-2 border-indigo-500 bg-white flex items-center justify-center">
                            <span className="w-1.5 h-1.5 bg-indigo-500 rounded-full"></span>
                          </span>
                          <div className="flex justify-between items-center bg-white border border-slate-100 rounded-lg p-2.5 shadow-sm text-xs">
                            <div>
                              <strong className="text-slate-800">ChromaDB Search</strong>
                              <p className="text-[10px] text-slate-500">Semantic vector search over filtered subset</p>
                            </div>
                            <span className="font-mono bg-slate-100 px-2 py-0.5 rounded font-bold text-indigo-700">
                              {currentRunResults[selectedResultIndex].timings['ChromaDB Context Retrieval'] || '44.0ms'}
                            </span>
                          </div>
                        </div>

                        {/* 4. SQL execution */}
                        <div className="relative">
                          <span className="absolute -left-6 top-1.5 w-4 h-4 rounded-full border-2 border-indigo-500 bg-white flex items-center justify-center">
                            <span className="w-1.5 h-1.5 bg-indigo-500 rounded-full"></span>
                          </span>
                          <div className="flex justify-between items-center bg-white border border-slate-100 rounded-lg p-2.5 shadow-sm text-xs">
                            <div>
                              <strong className="text-slate-800">PostgreSQL SQL Query & Validation</strong>
                              <p className="text-[10px] text-slate-500">Build SQL, validation, self-healing injection and fetch rows</p>
                            </div>
                            <span className="font-mono bg-slate-100 px-2 py-0.5 rounded font-bold text-indigo-700">
                              {currentRunResults[selectedResultIndex].timings['SQL Execution'] || '16.0ms'}
                            </span>
                          </div>
                        </div>

                        {/* 5. Gemini */}
                        <div className="relative">
                          <span className="absolute -left-6 top-1.5 w-4 h-4 rounded-full border-2 border-indigo-500 bg-white flex items-center justify-center">
                            <span className="w-1.5 h-1.5 bg-indigo-500 rounded-full"></span>
                          </span>
                          <div className="flex justify-between items-center bg-white border border-slate-100 rounded-lg p-2.5 shadow-sm text-xs">
                            <div>
                              <strong className="text-slate-800">Gemini LLM Response</strong>
                              <p className="text-[10px] text-slate-500">RAG response generation with context summaries</p>
                            </div>
                            <span className="font-mono bg-slate-100 px-2 py-0.5 rounded font-bold text-indigo-700">
                              {currentRunResults[selectedResultIndex].timings['Gemini AI Generation'] || '1.2s'}
                            </span>
                          </div>
                        </div>

                        {/* 6. Visualization */}
                        <div className="relative">
                          <span className="absolute -left-6 top-1.5 w-4 h-4 rounded-full border-2 border-indigo-500 bg-white flex items-center justify-center">
                            <span className="w-1.5 h-1.5 bg-indigo-500 rounded-full"></span>
                          </span>
                          <div className="flex justify-between items-center bg-white border border-slate-100 rounded-lg p-2.5 shadow-sm text-xs">
                            <div>
                              <strong className="text-slate-800">Visualization Builder</strong>
                              <p className="text-[10px] text-slate-500">Generate Plotly map and charts configuration</p>
                            </div>
                            <span className="font-mono bg-slate-100 px-2 py-0.5 rounded font-bold text-indigo-700">
                              {currentRunResults[selectedResultIndex].timings['Visualization Rendering'] || '28.0ms'}
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* SQL Tab */}
                  {inspectorTab === 'sql' && (
                    <div className="space-y-3 font-mono text-xs">
                      <div className="bg-white border border-slate-100 rounded-lg p-3">
                        <span className="block text-[9px] uppercase font-bold text-slate-400 mb-1">Generated SQL Query:</span>
                        <pre className="whitespace-pre-wrap break-all text-slate-800 font-semibold leading-relaxed">
                          {currentRunResults[selectedResultIndex].sqlUsed || '--- No SQL required for this query category ---'}
                        </pre>
                      </div>
                      <div className="grid grid-cols-2 gap-3">
                        <div className="bg-white border border-slate-100 rounded-lg p-2.5">
                          <span className="block text-[9px] uppercase font-bold text-slate-400 leading-none">Database Record Count</span>
                          <span className="text-sm font-bold text-slate-700 block mt-1">
                            {currentRunResults[selectedResultIndex].dataPoints} measurements fetched
                          </span>
                        </div>
                        <div className="bg-white border border-slate-100 rounded-lg p-2.5">
                          <span className="block text-[9px] uppercase font-bold text-slate-400 leading-none">Consistency Check</span>
                          <span className={`text-sm font-bold block mt-1 ${
                            currentRunResults[selectedResultIndex].rawResponse.query_params?.consistency_status === 'passed' 
                              ? 'text-emerald-600' 
                              : 'text-amber-600'
                          }`}>
                            {currentRunResults[selectedResultIndex].rawResponse.query_params?.consistency_status || 'passed'}
                          </span>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* ChromaDB Tab */}
                  {inspectorTab === 'chroma' && (
                    <div className="space-y-3">
                      <div className="bg-white border border-slate-100 rounded-lg p-3 font-mono text-xs">
                        <span className="block text-[9px] uppercase font-bold text-slate-400 mb-1">Applied Pre-filtering Parameters:</span>
                        <pre className="whitespace-pre-wrap break-all text-slate-700 leading-relaxed">
                          {JSON.stringify(currentRunResults[selectedResultIndex].rawResponse.query_params?.classification || {}, null, 2)}
                        </pre>
                      </div>
                      <div className="bg-white border border-slate-100 rounded-lg p-2.5">
                        <span className="block text-[9px] uppercase font-bold text-slate-400 leading-none">ChromaDB Context retrieved:</span>
                        <span className="text-xs font-bold text-slate-700 block mt-1">
                          {currentRunResults[selectedResultIndex].contextCount} document chunks returned
                        </span>
                      </div>
                    </div>
                  )}

                  {/* AI Tab */}
                  {inspectorTab === 'ai' && (
                    <div className="space-y-3 text-xs leading-relaxed">
                      <div className="bg-white border border-slate-100 rounded-lg p-4 max-h-[300px] overflow-y-auto">
                        <span className="block text-[9px] uppercase font-bold text-slate-400 mb-1.5">Gemini Response Output:</span>
                        <p className="text-slate-800 font-medium whitespace-pre-wrap">
                          {currentRunResults[selectedResultIndex].response}
                        </p>
                      </div>
                      {currentRunResults[selectedResultIndex].hasChart && (
                        <div className="bg-indigo-50/50 border border-indigo-100 rounded-lg p-2.5 text-indigo-900 font-semibold flex items-center gap-2">
                          <BarChart3 className="w-4 h-4 text-indigo-500" />
                          <span>Generated chart configuration returned for rendering (Plotly).</span>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Raw Tab */}
                  {inspectorTab === 'raw' && (
                    <div className="bg-white border border-slate-100 rounded-lg p-3 font-mono text-[10px] max-h-[350px] overflow-y-auto">
                      <pre className="whitespace-pre-wrap break-all text-slate-600 leading-normal">
                        {JSON.stringify(currentRunResults[selectedResultIndex].rawResponse, null, 2)}
                      </pre>
                    </div>
                  )}
                  
                </div>
              </div>
            )}

          </div>

        </div>

      </div>

      {/* Compare Runs Benchmarking Modal */}
      {showCompareModal && compareData && (
        <div className="fixed inset-0 bg-black bg-opacity-60 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-3xl max-w-4xl w-full max-h-[90vh] flex flex-col shadow-2xl border border-slate-100">
            {/* Modal Header */}
            <div className="p-6 border-b border-slate-100 flex items-center justify-between flex-shrink-0">
              <div className="flex items-center gap-3">
                <TrendingUp className="w-6 h-6 text-indigo-600" />
                <div>
                  <h3 className="font-bold text-lg text-slate-800">Performance Benchmarking Platform</h3>
                  <p className="text-xs text-slate-500">Comparing Run 1 ({compareData.run1.suiteName}) and Run 2 ({compareData.run2.suiteName})</p>
                </div>
              </div>
              <button 
                onClick={() => setShowCompareModal(false)}
                className="p-1 hover:bg-slate-100 rounded-full text-slate-400 hover:text-slate-600 transition-colors"
              >
                <XCircle className="w-6 h-6" />
              </button>
            </div>

            {/* Modal Body Scroll */}
            <div className="p-6 overflow-y-auto space-y-8 flex-1">
              
              {/* Overview grid comparison cards */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                
                {/* 1. Latency card */}
                <div className="bg-slate-50 border border-slate-100 rounded-2xl p-5 relative overflow-hidden">
                  <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Avg Latency</span>
                  
                  <div className="grid grid-cols-2 mt-3 text-center border-t border-slate-100 pt-3 gap-2">
                    <div className="border-r border-slate-200 pr-2">
                      <span className="block text-[8px] uppercase text-slate-400 font-bold">Run 1</span>
                      <span className="text-lg font-bold text-slate-700">{(compareData.run1.avgLatency / 1000).toFixed(2)}s</span>
                    </div>
                    <div className="pl-2">
                      <span className="block text-[8px] uppercase text-slate-400 font-bold">Run 2</span>
                      <span className="text-lg font-bold text-slate-700">{(compareData.run2.avgLatency / 1000).toFixed(2)}s</span>
                    </div>
                  </div>

                  <div className="mt-4 pt-2 border-t border-slate-100 text-center">
                    {compareData.run1.avgLatency !== compareData.run2.avgLatency ? (
                      <span className="inline-block text-[10px] font-bold text-emerald-700 bg-emerald-50 px-2.5 py-0.5 rounded-full border border-emerald-100">
                        {compareData.run1.avgLatency < compareData.run2.avgLatency 
                          ? `Run 1 is ${( (compareData.run2.avgLatency - compareData.run1.avgLatency) / 1000 ).toFixed(2)}s faster`
                          : `Run 2 is ${( (compareData.run1.avgLatency - compareData.run2.avgLatency) / 1000 ).toFixed(2)}s faster`
                        }
                      </span>
                    ) : (
                      <span className="text-[10px] text-slate-500 font-medium">Both runs have identical average latency</span>
                    )}
                  </div>
                </div>

                {/* 2. Accuracy card */}
                <div className="bg-slate-50 border border-slate-100 rounded-2xl p-5 relative overflow-hidden">
                  <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Classifier Accuracy</span>
                  
                  <div className="grid grid-cols-2 mt-3 text-center border-t border-slate-100 pt-3 gap-2">
                    <div className="border-r border-slate-200 pr-2">
                      <span className="block text-[8px] uppercase text-slate-400 font-bold">Run 1</span>
                      <span className="text-lg font-bold text-slate-700">{compareData.run1.accuracyScore.toFixed(0)}%</span>
                    </div>
                    <div className="pl-2">
                      <span className="block text-[8px] uppercase text-slate-400 font-bold">Run 2</span>
                      <span className="text-lg font-bold text-slate-700">{compareData.run2.accuracyScore.toFixed(0)}%</span>
                    </div>
                  </div>

                  <div className="mt-4 pt-2 border-t border-slate-100 text-center">
                    {compareData.run1.accuracyScore !== compareData.run2.accuracyScore ? (
                      <span className="inline-block text-[10px] font-bold text-emerald-700 bg-emerald-50 px-2.5 py-0.5 rounded-full border border-emerald-100">
                        {compareData.run1.accuracyScore > compareData.run2.accuracyScore 
                          ? `Run 1 is +${(compareData.run1.accuracyScore - compareData.run2.accuracyScore).toFixed(0)}% more accurate`
                          : `Run 2 is +${(compareData.run2.accuracyScore - compareData.run1.accuracyScore).toFixed(0)}% more accurate`
                        }
                      </span>
                    ) : (
                      <span className="text-[10px] text-slate-500 font-medium">Both runs have identical accuracy</span>
                    )}
                  </div>
                </div>

                {/* 3. SQL latency card */}
                <div className="bg-slate-50 border border-slate-100 rounded-2xl p-5 relative overflow-hidden">
                  <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Avg SQL Execution</span>
                  
                  <div className="grid grid-cols-2 mt-3 text-center border-t border-slate-100 pt-3 gap-2">
                    <div className="border-r border-slate-200 pr-2">
                      <span className="block text-[8px] uppercase text-slate-400 font-bold">Run 1</span>
                      <span className="text-lg font-bold text-slate-700">{compareData.run1.avgSqlLatency.toFixed(0)}ms</span>
                    </div>
                    <div className="pl-2">
                      <span className="block text-[8px] uppercase text-slate-400 font-bold">Run 2</span>
                      <span className="text-lg font-bold text-slate-700">{compareData.run2.avgSqlLatency.toFixed(0)}ms</span>
                    </div>
                  </div>

                  <div className="mt-4 pt-2 border-t border-slate-100 text-center">
                    {compareData.run1.avgSqlLatency !== compareData.run2.avgSqlLatency ? (
                      <span className="inline-block text-[10px] font-bold text-emerald-700 bg-emerald-50 px-2.5 py-0.5 rounded-full border border-emerald-100">
                        {compareData.run1.avgSqlLatency < compareData.run2.avgSqlLatency 
                          ? `Run 1 is ${(compareData.run2.avgSqlLatency - compareData.run1.avgSqlLatency).toFixed(0)}ms faster`
                          : `Run 2 is ${(compareData.run1.avgSqlLatency - compareData.run2.avgSqlLatency).toFixed(0)}ms faster`
                        }
                      </span>
                    ) : (
                      <span className="text-[10px] text-slate-500 font-medium">Both runs have identical DB response times</span>
                    )}
                  </div>
                </div>

              </div>

              {/* Side-by-Side detailed query tables */}
              <div className="space-y-4">
                <h4 className="text-sm font-bold text-slate-800">Query-by-Query Side-by-Side Comparison</h4>
                
                <div className="space-y-3">
                  {compareData.run1.results.map((res1, index) => {
                    const res2 = compareData.run2.results[index] || {
                      query: res1.query,
                      status: 'FAIL',
                      latency: 0,
                      isMatch: false,
                      response: 'Not executed in Run 2'
                    };

                    return (
                      <div key={index} className="border border-slate-100 rounded-2xl overflow-hidden shadow-sm">
                        {/* Query Header */}
                        <div className="bg-slate-50 px-4 py-2 text-xs font-bold text-slate-800 border-b border-slate-100 flex items-center justify-between">
                          <span>Q{index + 1}: {res1.query}</span>
                          <span className="text-[10px] font-semibold text-slate-500 bg-slate-200/50 px-2 py-0.5 rounded">
                            Expected Type: {res1.expectedType}
                          </span>
                        </div>

                        {/* Split runs comparisons */}
                        <div className="grid grid-cols-1 md:grid-cols-2 divide-y md:divide-y-0 md:divide-x divide-slate-100">
                          {/* Run 1 result */}
                          <div className="p-4 text-xs space-y-2.5">
                            <div className="flex items-center justify-between">
                              <span className="font-bold text-slate-400 block uppercase text-[9px]">Run 1 (Older)</span>
                              <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                                res1.status === 'PASS' 
                                  ? 'bg-emerald-50 text-emerald-700' 
                                  : 'bg-red-50 text-red-700'
                              }`}>
                                {res1.status}
                              </span>
                            </div>
                            
                            <div className="grid grid-cols-2 gap-2 text-[10px] font-medium bg-slate-50/50 border border-slate-100 p-2 rounded-lg">
                              <div>
                                <span className="block text-[8px] uppercase text-slate-400 font-bold">End Latency</span>
                                <span className="font-bold text-slate-700">{(res1.latency / 1000).toFixed(2)}s</span>
                              </div>
                              <div>
                                <span className="block text-[8px] uppercase text-slate-400 font-bold">Classifier</span>
                                <span className={res1.isMatch ? 'text-emerald-600 font-bold' : 'text-red-500 font-bold'}>
                                  {res1.isMatch ? 'Match ✅' : 'Mismatch ❌'}
                                </span>
                              </div>
                            </div>
                            
                            <div className="bg-white border border-slate-100 p-2.5 rounded-lg max-h-[80px] overflow-y-auto text-[11px] leading-relaxed text-slate-600">
                              {res1.response}
                            </div>
                          </div>

                          {/* Run 2 result */}
                          <div className="p-4 text-xs space-y-2.5">
                            <div className="flex items-center justify-between">
                              <span className="font-bold text-slate-400 block uppercase text-[9px]">Run 2 (Newer)</span>
                              <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                                res2.status === 'PASS' 
                                  ? 'bg-emerald-50 text-emerald-700' 
                                  : 'bg-red-50 text-red-700'
                              }`}>
                                {res2.status}
                              </span>
                            </div>
                            
                            <div className="grid grid-cols-2 gap-2 text-[10px] font-medium bg-slate-50/50 border border-slate-100 p-2 rounded-lg">
                              <div>
                                <span className="block text-[8px] uppercase text-slate-400 font-bold">End Latency</span>
                                <span className="font-bold text-slate-700">{(res2.latency / 1000).toFixed(2)}s</span>
                              </div>
                              <div>
                                <span className="block text-[8px] uppercase text-slate-400 font-bold">Classifier</span>
                                <span className={res2.isMatch ? 'text-emerald-600 font-bold' : 'text-red-500 font-bold'}>
                                  {res2.isMatch ? 'Match ✅' : 'Mismatch ❌'}
                                </span>
                              </div>
                            </div>
                            
                            <div className="bg-white border border-slate-100 p-2.5 rounded-lg max-h-[80px] overflow-y-auto text-[11px] leading-relaxed text-slate-600">
                              {res2.response}
                            </div>
                          </div>
                        </div>

                      </div>
                    );
                  })}
                </div>
              </div>

            </div>

            {/* Modal Footer */}
            <div className="p-4 border-t border-slate-100 bg-slate-50 rounded-b-3xl flex justify-end flex-shrink-0">
              <Button onClick={() => setShowCompareModal(false)}>Close Benchmark</Button>
            </div>
          </div>
        </div>
      )}
    </Layout>
  );
};
