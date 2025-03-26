import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Container, Row, Col } from 'react-bootstrap';
import { AnalyzerProvider } from './context/AnalyzerContext';

// Import pages
import UploadPage from './pages/UploadPage';
import AnalysisPage from './pages/AnalysisPage';
import ThreadsPage from './pages/ThreadsPage';

// Import components
import Sidebar from './components/common/Sidebar';

// Import styles
import 'bootstrap/dist/css/bootstrap.min.css';
import './App.css';

function App() {
  return (
    <AnalyzerProvider>
      <Router>
        <div className="app-container">
          <Sidebar />
          <main className="content-area">
            <Container fluid className="py-4">
              <Routes>
                <Route path="/" element={<UploadPage />} />
                <Route path="/analysis" element={<AnalysisPage />} />
                <Route path="/threads" element={<ThreadsPage />} />
              </Routes>
            </Container>
          </main>
        </div>
      </Router>
    </AnalyzerProvider>
  );
}

export default App;
