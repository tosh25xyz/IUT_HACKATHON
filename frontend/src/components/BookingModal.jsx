import { useState } from 'react'
import api from '../api/axios'

function BookingModal({ room, onClose, onSuccess }) {
  const [form, setForm] = useState({
    date: '',
    startHour: '09',
    duration: '1'
  })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      const startTime = new Date(`${form.date}T${form.startHour}:00:00Z`)
      const endTime = new Date(startTime)
      endTime.setHours(endTime.getHours() + parseInt(form.duration))

      await api.post('/bookings', {
        room_id: room.id,
        start_time: startTime.toISOString(),
        end_time: endTime.toISOString()
      })

      onSuccess()
    } catch (err) {
      const message = err.response?.data?.message || 'Failed to create booking'
      setError(message)
    } finally {
      setLoading(false)
    }
  }

  const hours = Array.from({ length: 16 }, (_, i) => {
    const h = i + 6
    return h.toString().padStart(2, '0')
  })

  const durations = [1, 2, 3, 4, 5, 6, 7, 8]

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h3>Book {room.name}</h3>
        
        {error && <div className="error">{error}</div>}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Date</label>
            <input
              type="date"
              value={form.date}
              onChange={(e) => setForm({ ...form, date: e.target.value })}
              min={new Date().toISOString().split('T')[0]}
              required
            />
          </div>

          <div className="form-row">
            <div className="form-group">
              <label>Start Time</label>
              <select
                value={form.startHour}
                onChange={(e) => setForm({ ...form, startHour: e.target.value })}
                required
              >
                {hours.map(h => (
                  <option key={h} value={h}>{h}:00</option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label>Duration (hours)</label>
              <select
                value={form.duration}
                onChange={(e) => setForm({ ...form, duration: e.target.value })}
                required
              >
                {durations.map(d => (
                  <option key={d} value={d}>{d} hour{d > 1 ? 's' : ''}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="form-group">
            <strong>Total Price: </strong>
            ${((room.hourly_rate_cents / 100) * parseInt(form.duration)).toFixed(2)}
          </div>

          <div className="modal-actions">
            <button type="button" className="btn btn-secondary" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? 'Booking...' : 'Confirm Booking'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default BookingModal
