import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api/axios'
import Rooms from '../components/Rooms'
import Bookings from '../components/Bookings'

function Dashboard({ setAuth }) {
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState('rooms')
  const [user, setUser] = useState({
    org_name: localStorage.getItem('org_name') || '',
    username: localStorage.getItem('username') || ''
  })

  const handleLogout = async () => {
    try {
      await api.post('/auth/logout')
    } catch (err) {
      console.error('Logout error:', err)
    } finally {
      localStorage.clear()
      setAuth(false)
      navigate('/login')
    }
  }

  return (
    <div>
      <nav className="navbar">
        <div className="navbar-content">
          <h1>🏢 CoWork</h1>
          <div className="navbar-user">
            <span>{user.org_name} / {user.username}</span>
            <button onClick={handleLogout}>Logout</button>
          </div>
        </div>
      </nav>

      <div className="container">
        <div className="tabs">
          <button 
            className={`tab ${activeTab === 'rooms' ? 'active' : ''}`}
            onClick={() => setActiveTab('rooms')}
          >
            Rooms
          </button>
          <button 
            className={`tab ${activeTab === 'bookings' ? 'active' : ''}`}
            onClick={() => setActiveTab('bookings')}
          >
            My Bookings
          </button>
        </div>

        {activeTab === 'rooms' && <Rooms />}
        {activeTab === 'bookings' && <Bookings />}
      </div>
    </div>
  )
}

export default Dashboard
