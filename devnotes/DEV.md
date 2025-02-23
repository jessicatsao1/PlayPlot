# Hackathon Project Development Guide

## Project Overview
This project is a hackathon application that integrates advanced AI capabilities using ElevenLabs and Fal.ai APIs.

## Tech Stack
- Frontend: [Your frontend framework]
- Backend: [Your backend framework]
- AI Services:
  - ElevenLabs API for voice synthesis
  - Fal.ai API for AI processing

## Getting Started

### Prerequisites
- Node.js (latest LTS version recommended)
- Git
- npm or yarn

### Environment Setup
1. Clone the repository:
```bash
git clone git@github.com:PeterL-1111/hackathon.git
cd hackathon
```

2. Create a `.env` file in the root directory with the following variables:
```env
ELEVENLABS_API_KEY=your_key_here
fal_ai_api=your_key_here
```

### Installation
```bash
npm install
# or
yarn install
```

### Development
```bash
npm run dev
# or
yarn dev
```

## Git Workflow

### Branch Strategy
- `main` - production-ready code
- `develop` - development branch
- Feature branches should follow the format: `feature/feature-name`

### Commit Guidelines
- Use clear, descriptive commit messages
- Format: `type(scope): description`
- Types: feat, fix, docs, style, refactor, test, chore

### Protected Files
The following files and directories are ignored in Git:
- `.env` (contains sensitive API keys)
- `node_modules/`
- Build directories
- Log files
- IDE configuration files

## API Integration

### ElevenLabs API
- Used for: [Description of ElevenLabs usage]
- Documentation: [Link to ElevenLabs docs]
- Implementation details: [Brief overview]

### Fal.ai API
- Used for: [Description of Fal.ai usage]
- Documentation: [Link to Fal.ai docs]
- Implementation details: [Brief overview]

## Best Practices
1. Never commit sensitive information
2. Keep environment variables in `.env` file
3. Document new features and API integrations
4. Follow the established code style
5. Write tests for new features

## Deployment
[Add deployment instructions specific to your setup]

## Contributing
1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## Support
For any questions or issues, please:
1. Check existing issues
2. Create a new issue with detailed description
3. Contact the development team

## License
[Your project license] 