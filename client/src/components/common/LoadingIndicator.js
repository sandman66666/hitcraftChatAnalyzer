import React from 'react';

const LoadingIndicator = ({ message = 'Loading...' }) => {
  return (
    <div className="loading-container">
      <div className="spinner-border text-primary" role="status">
        <span className="visually-hidden">Loading...</span>
      </div>
      <p className="loading-message mt-3">{message}</p>
    </div>
  );
};

export default LoadingIndicator;
