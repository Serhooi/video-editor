import { useState } from 'react'
import { Transitions } from './features/editor/menu-item/transitions'
import { Music } from './features/editor/menu-item/music'
import Timeline from './components/timeline'
import './App.css'

function App() {
  const [activeTab, setActiveTab] = useState('transitions')

  return (
    <div className="h-screen flex flex-col bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-4 py-3">
        <h1 className="text-xl font-bold text-gray-900">Video Editor - Drag & Drop Fixed</h1>
        <p className="text-sm text-gray-600">Test drag & drop functionality for transitions and music</p>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar */}
        <div className="w-80 bg-white border-r border-gray-200 flex flex-col">
          {/* Tab Navigation */}
          <div className="flex border-b border-gray-200">
            <button
              onClick={() => setActiveTab('transitions')}
              className={`flex-1 px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'transitions'
                  ? 'border-blue-500 text-blue-600 bg-blue-50'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:bg-gray-50'
              }`}
            >
              🎬 Transitions
            </button>
            <button
              onClick={() => setActiveTab('music')}
              className={`flex-1 px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'music'
                  ? 'border-blue-500 text-blue-600 bg-blue-50'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:bg-gray-50'
              }`}
            >
              🎵 Music
            </button>
          </div>

          {/* Tab Content */}
          <div className="flex-1 overflow-hidden">
            {activeTab === 'transitions' && <Transitions />}
            {activeTab === 'music' && <Music />}
          </div>
        </div>

        {/* Timeline Area */}
        <Timeline />
      </div>

      {/* Instructions */}
      <div className="bg-blue-50 border-t border-blue-200 px-4 py-3">
        <div className="text-sm text-blue-800">
          <strong>Instructions:</strong> 
          <span className="ml-2">
            1. Switch between Transitions and Music tabs in the sidebar
          </span>
          <span className="mx-2">•</span>
          <span>
            2. Drag items from the sidebar to the timeline area
          </span>
          <span className="mx-2">•</span>
          <span>
            3. Check the console for drag & drop events
          </span>
        </div>
      </div>
    </div>
  )
}

export default App

