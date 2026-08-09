import { Routes, Route } from 'react-router-dom'
import HomePage from './pages/HomePage'
import AnalysisPage from './pages/AnalysisPage'
import ResultPage from './pages/ResultPage'
import HistoryPage from './pages/HistoryPage'
import BasicsPage from './pages/BasicsPage'
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
        {/* /ontology·/ptontology 라우트 삭제(2026-08-09) — 온톨로지는 서빙에 직접 관여하지
            않는다는 원칙대로 내부 도구화. 페이지 컴포넌트 파일은 남겨둔다(내부 디버깅용 복원 여지) */}
      </Routes>
    </Layout>
  )
}

export default App
