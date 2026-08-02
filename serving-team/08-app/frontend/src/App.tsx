import { Routes, Route } from 'react-router-dom'
import HomePage from './pages/HomePage'
import AnalysisPage from './pages/AnalysisPage'
import ResultPage from './pages/ResultPage'
import HistoryPage from './pages/HistoryPage'
import BasicsPage from './pages/BasicsPage'
import OntologyPage from './pages/OntologyPage'
import PtOntologyPage from './pages/PtOntologyPage'
import Layout from './components/common/Layout'

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/analysis" element={<AnalysisPage />} />
        <Route path="/result/:id" element={<ResultPage />} />
        <Route path="/history" element={<HistoryPage />} />
        {/* 사진과 무관하게 늘 지켜야 하는 것. 앵커 정확도와 무관하게 항상 맞는 유일한 화면 */}
        <Route path="/basics" element={<BasicsPage />} />
        <Route path="/ontology" element={<OntologyPage />} />
        <Route path="/ptontology" element={<PtOntologyPage />} />
      </Routes>
    </Layout>
  )
}

export default App
