import { Link } from 'react-router-dom'
import { Compass } from 'lucide-react'
import { Empty } from '../components/ui'

export default function NotFound() {
  return (
    <div className="page">
      <Empty title="Page not found" icon={<Compass size={26} />}>
        That route doesn’t exist. Press <span className="kbd">Ctrl K</span> to search, or return to <Link to="/">Markets</Link>.
      </Empty>
    </div>
  )
}
