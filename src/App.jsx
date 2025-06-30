import { useState } from 'react'
import { Transitions } from './features/editor/menu-item/transitions'
import { Music } from './features/editor/menu-item/music'
import { Timeline } from './components/timeline'
import { Button } from '@/components/ui/button.jsx'
import { Music as MusicIcon, Zap } from 'lucide-react'
import './App.css'

function App() {
  const [activeTab, setActiveTab] = useState('transitions')

  return (
    <div className="flex h-screen bg-gray-100">
      {/* Sidebar */}
      <div className="w-80 bg-white border-r border-gray-200 flex flex-col">
        {/* Header */}
        <div className="p-4 border-b border-gray-200">
          <h1 className="text-xl font-bold text-gray-800">Video Editor</h1>
          <p className="text-sm text-gray-600">Drag & Drop Fixed</p>
        </div>
        
        {/* Tabs */}
        <div className="flex border-b border-gray-200">
          <Button
            variant={activeTab === 'transitions' ? 'default' : 'ghost'}
            className="flex-1 rounded-none"
            onClick={() => setActiveTab('transitions')}
          >
            <Zap className="w-4 h-4 mr-2" />
            Transitions
          </Button>
          <Button
            variant={activeTab === 'music' ? 'default' : 'ghost'}
            className="flex-1 rounded-none"
            onClick={() => setActiveTab('music')}
          >
            <MusicIcon className="w-4 h-4 mr-2" />
            Music
          </Button>
        </div>
        
        {/* Content */}
        <div className="flex-1 overflow-hidden">
          {activeTab === 'transitions' && <Transitions />}
          {activeTab === 'music' && <Music />}
        </div>
      </div>
      
      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        {/* Top Bar */}
        <div className="h-16 bg-white border-b border-gray-200 flex items-center px-6">
          <h2 className="text-lg font-semibold text-gray-800">Video Editor - Drag & Drop Test</h2>
        </div>
        
        {/* Timeline Area */}
        <div className="flex-1 p-6">
          <Timeline className="w-full" />
        </div>
      </div>
    </div>
  )
}

export default App

