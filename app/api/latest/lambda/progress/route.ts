import { NextRequest, NextResponse } from 'next/server';
import { types } from '@/lib/types';

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    
    // Process progress update
    console.log('Progress update received:', body);
    
    return NextResponse.json({ success: true });
  } catch (error) {
    console.error('Error processing progress update:', error);
    return NextResponse.json(
      { error: 'Failed to process progress update' },
      { status: 500 }
    );
  }
}

export const dynamic = 'force-dynamic';

