# PlayPlot

PlayPlot is an interactive storytelling platform that combines AI-generated narratives with multimedia elements to create immersive story experiences.

## Prerequisites

### Node.js Environment
- Node.js (v18 or higher)
- npm (comes with Node.js) or pnpm

### Python Environment
- Python 3.9 or higher
- pip (Python package manager)

### API Keys Required
The following API keys need to be set up in the `backend/.env` file:
```env
OPENAI_API_KEY=your_openai_api_key
ELEVENLABS_API_KEY=your_elevenlabs_api_key
PERPLEXITY_API_KEY=your_perplexity_api_key
GROQ_API_KEY=your_groq_api_key
FAL_KEY=your_fal_api_key
```

## Installation

### Backend Setup
1. Navigate to the backend directory:
```bash
cd backend
```

2. Create a Python virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
```

3. Install Python dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the backend and frontend directory and add your API keys as shown in the Prerequisites section.

### Frontend Setup
1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
# or if using pnpm
pnpm install
```

## Running the Application

### Start the Backend Server
1. From the backend directory:
```bash
python api.py
```
The backend server will start on `http://localhost:5000`

### Start the Frontend Development Server
1. From the frontend directory:
```bash
npm run dev
# or with pnpm
pnpm dev
```
The frontend will be available at `http://localhost:3000`

## Project Structure

```
PlayPlot/
├── backend/           # Python Flask backend
│   ├── api.py        # Main API endpoints
│   ├── requirements.txt
│   └── ...
├── frontend/         # Next.js frontend
│   ├── app/         # Next.js pages and components
│   ├── components/  # Reusable React components
│   └── ...
└── screenshot-demo/  # Demo screenshots and media
```

## Features
- AI-powered story generation
- Text-to-speech conversion
- Image generation
- Video creation
- Interactive story progression
- Real-time updates

## Contributing
Please read our contributing guidelines before submitting pull requests.

## License
This project is licensed under the MIT License - see the LICENSE file for details.
