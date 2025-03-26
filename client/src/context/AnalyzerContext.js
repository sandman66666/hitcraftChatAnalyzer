import React, { createContext, useContext, useReducer, useEffect, useState, useRef, useCallback } from 'react';

// Initial application state
const initialState = {
  sessionId: null,
  filename: null,
  processingActive: false,
  threadExtracted: false,
  threadCount: 0,
  threadsToAnalyze: 0,
  threadsAnalyzed: 0,
  analysisInProgress: false,
  analysisComplete: false,
  logs: [],
  results: null,
  threads: [],
  currentThread: null,
  error: null
};

// Action types
const ActionTypes = {
  SET_SESSION: 'SET_SESSION',
  SET_THREAD_EXTRACTED: 'SET_THREAD_EXTRACTED',
  SET_THREAD_COUNT: 'SET_THREAD_COUNT',
  START_ANALYSIS: 'START_ANALYSIS',
  UPDATE_ANALYSIS_PROGRESS: 'UPDATE_ANALYSIS_PROGRESS',
  COMPLETE_ANALYSIS: 'COMPLETE_ANALYSIS',
  SET_LOGS: 'SET_LOGS',
  ADD_LOG: 'ADD_LOG',
  SET_RESULTS: 'SET_RESULTS',
  SET_THREADS: 'SET_THREADS',
  SET_CURRENT_THREAD: 'SET_CURRENT_THREAD',
  SET_ERROR: 'SET_ERROR',
  RESET_STATE: 'RESET_STATE'
};

// Reducer function for state updates
const analyzerReducer = (state, action) => {
  switch (action.type) {
    case ActionTypes.SET_SESSION:
      return {
        ...state,
        sessionId: action.payload.sessionId,
        filename: action.payload.filename,
        error: null
      };
    
    case ActionTypes.SET_THREAD_EXTRACTED:
      return {
        ...state,
        threadExtracted: action.payload,
        error: null
      };
    
    case ActionTypes.SET_THREAD_COUNT:
      return {
        ...state,
        threadCount: action.payload,
        error: null
      };
    
    case ActionTypes.START_ANALYSIS:
      return {
        ...state,
        analysisInProgress: true,
        threadsToAnalyze: action.payload,
        threadsAnalyzed: 0,
        analysisComplete: false,
        error: null
      };
    
    case ActionTypes.UPDATE_ANALYSIS_PROGRESS:
      return {
        ...state,
        threadsAnalyzed: action.payload,
        error: null
      };
    
    case ActionTypes.COMPLETE_ANALYSIS:
      return {
        ...state,
        analysisInProgress: false,
        analysisComplete: true,
        results: action.payload,
        error: null
      };
    
    case ActionTypes.SET_LOGS:
      return {
        ...state,
        logs: action.payload
      };
    
    case ActionTypes.ADD_LOG:
      return {
        ...state,
        logs: [...state.logs, action.payload]
      };
    
    case ActionTypes.SET_RESULTS:
      return {
        ...state,
        results: action.payload,
        error: null
      };
    
    case ActionTypes.SET_THREADS:
      return {
        ...state,
        threads: action.payload,
        error: null
      };
    
    case ActionTypes.SET_CURRENT_THREAD:
      return {
        ...state,
        currentThread: action.payload,
        error: null
      };
    
    case ActionTypes.SET_ERROR:
      return {
        ...state,
        error: action.payload
      };
    
    case ActionTypes.RESET_STATE:
      return {
        ...initialState
      };
    
    default:
      return state;
  }
};

// Create the context
const AnalyzerContext = createContext();

// Context provider component
export const AnalyzerProvider = ({ children }) => {
  const [state, dispatch] = useReducer(analyzerReducer, initialState);
  
  // For debugging purposes
  useEffect(() => {
    console.log('Analyzer state updated:', state);
  }, [state]);
  
  // Expose the context value
  const contextValue = {
    state,
    dispatch,
    actions: {
      setSession: (sessionId, filename) => {
        dispatch({
          type: ActionTypes.SET_SESSION,
          payload: { sessionId, filename }
        });
      },
      setThreadExtracted: (extracted) => {
        dispatch({
          type: ActionTypes.SET_THREAD_EXTRACTED,
          payload: extracted
        });
      },
      setThreadCount: (count) => {
        dispatch({
          type: ActionTypes.SET_THREAD_COUNT,
          payload: count
        });
      },
      startAnalysis: (threadCount) => {
        dispatch({
          type: ActionTypes.START_ANALYSIS,
          payload: threadCount
        });
      },
      updateAnalysisProgress: (threadsAnalyzed) => {
        dispatch({
          type: ActionTypes.UPDATE_ANALYSIS_PROGRESS,
          payload: threadsAnalyzed
        });
      },
      completeAnalysis: (results) => {
        dispatch({
          type: ActionTypes.COMPLETE_ANALYSIS,
          payload: results
        });
      },
      setLogs: (logs) => {
        dispatch({
          type: ActionTypes.SET_LOGS,
          payload: logs
        });
      },
      addLog: (log) => {
        dispatch({
          type: ActionTypes.ADD_LOG,
          payload: log
        });
      },
      setResults: (results) => {
        dispatch({
          type: ActionTypes.SET_RESULTS,
          payload: results
        });
      },
      setThreads: (threads) => {
        dispatch({
          type: ActionTypes.SET_THREADS,
          payload: threads
        });
      },
      setCurrentThread: (thread) => {
        dispatch({
          type: ActionTypes.SET_CURRENT_THREAD,
          payload: thread
        });
      },
      setError: (error) => {
        dispatch({
          type: ActionTypes.SET_ERROR,
          payload: error
        });
      },
      resetState: () => {
        dispatch({ type: ActionTypes.RESET_STATE });
      }
    }
  };
  
  return (
    <AnalyzerContext.Provider value={contextValue}>
      {children}
    </AnalyzerContext.Provider>
  );
};

// Custom hook for using the analyzer context
export const useAnalyzer = () => {
  const context = useContext(AnalyzerContext);
  if (!context) {
    throw new Error('useAnalyzer must be used within an AnalyzerProvider');
  }
  return context;
};

export default AnalyzerContext;
