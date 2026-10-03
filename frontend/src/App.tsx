import { Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import AskPage from './pages/AskPage'
import ConfigPage from './pages/ConfigPage'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<AskPage />} />
        <Route path="config" element={<ConfigPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}
