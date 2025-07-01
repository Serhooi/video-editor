// Health check endpoint for Docker
export default function handler(req, res) {
  if (req.method === 'GET') {
    res.status(200).json({ 
      status: 'ok', 
      timestamp: new Date().toISOString(),
      service: 'React Video Editor Pro',
      version: '7.0.0'
    });
  } else {
    res.setHeader('Allow', ['GET']);
    res.status(405).end(`Method ${req.method} Not Allowed`);
  }
}

