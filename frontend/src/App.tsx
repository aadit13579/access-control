import { BrowserRouter, Routes, Route } from 'react-router-dom';

import { AppHeader } from './components/AppHeader';
import { JobsPage } from './pages/JobsPage';
import { JobDetailsPage } from './pages/JobDetailsPage';
import { WaitingPage } from './pages/WaitingPage';
import { AuthorizationPage } from './pages/AuthorizationPage';
import { GrantsPage } from './pages/GrantsPage';
import { ApprovalsPage } from './pages/ApprovalsPage';

function App() {
  return (
    <BrowserRouter>
      <AppHeader />

      <main style={{ padding: '5rem 2rem 2rem' }}>
        <Routes>
          <Route path="/" element={<JobsPage />} />
          <Route path="/jobs" element={<JobsPage />} />
          <Route path="/jobs/:jobId" element={<JobDetailsPage />} />
          <Route path="/waiting" element={<WaitingPage />} />
          <Route path="/authorization" element={<AuthorizationPage />} />
          <Route path='/grants' element={<GrantsPage />}/>
          <Route path="/approvals" element={<ApprovalsPage />}/>
        </Routes>
      </main>
    </BrowserRouter>
  );
}

export default App;