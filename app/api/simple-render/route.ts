import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  try {
    console.log('🎬 Starting simple render process...');
    
    const body = await request.json();
    console.log('Render request:', body);

    // Simulate render process with delay
    await new Promise(resolve => setTimeout(resolve, 2000));

    // Return demo video URL for now
    const demoVideoUrl = 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4';
    
    console.log('✅ Simple render completed successfully');

    return NextResponse.json({
      success: true,
      message: 'Video rendered successfully!',
      videoUrl: demoVideoUrl,
      renderType: 'demo',
      duration: '2 seconds',
      timestamp: new Date().toISOString()
    });

  } catch (error: any) {
    console.error('❌ Simple render failed:', error);
    
    return NextResponse.json({
      success: false,
      error: error.message,
      details: 'Simple render process failed'
    }, { status: 500 });
  }
}

export async function GET() {
  return NextResponse.json({
    message: 'Simple render endpoint',
    status: 'ready',
    description: 'Simplified video render without AWS Lambda',
    demoMode: true
  });
}

