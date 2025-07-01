import Link from 'next/link';

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-24">
      <div className="z-10 max-w-5xl w-full items-center justify-between font-mono text-sm">
        <h1 className="text-4xl font-bold mb-8 text-center">React Video Editor Pro</h1>
        
        <div className="bg-white dark:bg-gray-800 p-8 rounded-lg shadow-lg">
          <h2 className="text-2xl font-semibold mb-4">Available Versions</h2>
          
          <div className="grid gap-4">
            <Link 
              href="/versions/7.0.0" 
              className="p-4 border rounded-md hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
            >
              <div className="font-medium">Version 7.0.0</div>
              <div className="text-sm text-gray-500 dark:text-gray-400">
                Full-featured video editor with transitions, captions, and more
              </div>
            </Link>
          </div>
        </div>
      </div>
    </main>
  );
}

