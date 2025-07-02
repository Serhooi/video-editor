import { NextRequest, NextResponse } from 'next/server';

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const renderId = searchParams.get('renderId');
    
    console.log('📊 Checking simple render progress for:', renderId);

    // Simulate progress tracking
    const progress = {
      renderId: renderId || 'demo-render-' + Date.now(),
      status: 'completed',
      progress: 100,
      message: 'Demo video ready!',
      videoUrl: 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4',
      timestamp: new Date().toISOString()
    };

    return NextResponse.json(progress);

  } catch (error: any) {
    console.error('❌ Progress check failed:', error);
    
    return NextResponse.json({
      status: 'error',
      error: error.message,
      progress: 0
    }, { status: 500 });
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    console.log('📊 Simple render progress update:', body);

    return NextResponse.json({
      success: true,
      message: 'Progress updated'
    });

  } catch (error: any) {
    console.error('❌ Progress update failed:', error);
    
    return NextResponse.json({
      success: false,
      error: error.message
    }, { status: 500 });
  }
}

