import { NextRequest, NextResponse } from 'next/server';
import { types } from '@/lib/types';

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    
    // Process render request
    console.log('Render request received:', body);
    
    return NextResponse.json({ 
      success: true,
      renderId: 'mock-render-id-' + Date.now(),
      status: 'started'
    });
  } catch (error) {
    console.error('Error processing render request:', error);
    return NextResponse.json(
      { error: 'Failed to process render request' },
      { status: 500 }
    );
  }
}

export const dynamic = 'force-dynamic';

