import { Navigate, Route, Routes } from 'react-router-dom'
import { lazy, Suspense, type ReactNode } from 'react'
import { Layout } from './components/Layout'
import { Spinner } from './components/ui'
import { useAuth, type Role } from './lib/auth'
import Login from './pages/Login'
const Register = lazy(() => import('./pages/Register'))
const Home = lazy(() => import('./pages/Home'))
const Profile = lazy(() => import('./pages/Profile'))
const Assessment = lazy(() => import('./pages/Assessment'))
const Interview = lazy(() => import('./pages/Interview'))
const Dashboard = lazy(() => import('./pages/Dashboard'))
const CategoryDetail = lazy(() => import('./pages/CategoryDetail'))
const Agents = lazy(() => import('./pages/Agents'))
const Recommendations = lazy(() => import('./pages/Recommendations'))
const Habits = lazy(() => import('./pages/Habits'))
const Reviews = lazy(() => import('./pages/Reviews'))
const Reports = lazy(() => import('./pages/Reports'))
const CoachPortal = lazy(() => import('./pages/CoachPortal'))
const Admin = lazy(() => import('./pages/Admin'))
const Privacy = lazy(() => import('./pages/Privacy'))
const Help = lazy(() => import('./pages/Help'))

function Guard({ children, roles }: { children: ReactNode; roles?: Role[] }) {
  const { user, loading } = useAuth()
  if (loading) return <Spinner />
  if (!user) return <Navigate to="/login" replace />
  if (roles && !roles.includes(user.user_role)) return <Navigate to="/" replace />
  return <Layout><Suspense fallback={<Spinner />}>{children}</Suspense></Layout>
}

export default function App() {
  return (
    <Suspense fallback={<Spinner />}>
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/" element={<Guard><Home /></Guard>} />
      <Route path="/profile" element={<Guard><Profile /></Guard>} />
      <Route path="/assessment" element={<Guard roles={['individual']}><Assessment /></Guard>} />
      <Route path="/interview" element={<Guard roles={['coach', 'counselor']}><Interview /></Guard>} />
      <Route path="/dashboard" element={<Guard roles={['individual', 'coach', 'counselor']}><Dashboard /></Guard>} />
      <Route path="/dashboard/:categoryId" element={<Guard roles={['individual', 'coach', 'counselor']}><CategoryDetail /></Guard>} />
      <Route path="/agents" element={<Guard><Agents /></Guard>} />
      <Route path="/recommendations" element={<Guard roles={['individual']}><Recommendations /></Guard>} />
      <Route path="/habits" element={<Guard roles={['individual']}><Habits /></Guard>} />
      <Route path="/reviews" element={<Guard roles={['individual', 'coach', 'counselor']}><Reviews /></Guard>} />
      <Route path="/reports" element={<Guard roles={['individual', 'coach', 'counselor']}><Reports /></Guard>} />
      <Route path="/coach" element={<Guard roles={['coach', 'counselor']}><CoachPortal /></Guard>} />
      <Route path="/admin" element={<Guard roles={['admin']}><Admin /></Guard>} />
      <Route path="/privacy" element={<Guard><Privacy /></Guard>} />
      <Route path="/help" element={<Guard><Help /></Guard>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
    </Suspense>
  )
}
