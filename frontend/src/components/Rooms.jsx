import { useState, useEffect } from 'react'
import api from '../api/axios'
import BookingModal from './BookingModal'

function Rooms() {
  const [rooms, setRooms] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selectedRoom, setSelectedRoom] = useState(null)
  const [showBookingModal, setShowBookingModal] = useState(false)

  useEffect(() => {
    fetchRooms()
  }, [])

  const fetchRooms = async () => {
    try {
      const { data } = await api.get('/rooms')
      setRooms(data)
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to load rooms')
    } finally {
      setLoading(false)
    }
  }

  const handleBook = (room) => {
    setSelectedRoom(room)
    setShowBookingModal(true)
  }

  const handleBookingSuccess = () => {
    setShowBookingModal(false)
    setSelectedRoom(null)
  }

  if (loading) return <div className="loading">Loading rooms...</div>
  if (error) return <div className="card"><div className="error">{error}</div></div>

  return (
    <div>
      <div className="card">
        <h3>Available Rooms</h3>
        {rooms.length === 0 ? (
          <div className="empty-state">
            <p>No rooms available yet.</p>
          </div>
        ) : (
          <div className="room-grid">
            {rooms.map(room => (
              <div key={room.id} className="room-card">
                <h4>{room.name}</h4>
                <div className="room-info">
                  <span>👥 Capacity: {room.capacity} people</span>
                  <span>💰 Rate: ${(room.hourly_rate_cents / 100).toFixed(2)}/hour</span>
                </div>
                <button 
                  className="btn btn-primary" 
                  onClick={() => handleBook(room)}
                >
                  Book Now
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {showBookingModal && (
        <BookingModal
          room={selectedRoom}
          onClose={() => setShowBookingModal(false)}
          onSuccess={handleBookingSuccess}
        />
      )}
    </div>
  )
}

export default Rooms
