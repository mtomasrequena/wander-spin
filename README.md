# WanderSpin 🌍🎲

> A collaborative, AI-powered travel planning application built with a gamified approach.

## 🚀 Overview

WanderSpin redefines trip organization by combining structured planning with an element of serendipity. Users can meticulously plan points of interest (POIs) or use the "Roulette Mode" to let the system suggest spontaneous destinations. The core engine leverages AI to generate intelligent, multimodal travel itineraries factoring in time, budget, and geographic constraints.

## 🛠️ Tech Stack

### Backend
*   **Framework:** Python / Django
*   **API:** Django REST Framework (DRF)
*   **Authentication:** SimpleJWT
*   **AI Integration:** Claude 3.5 Sonnet (routing logic), DALL-E (card generation)

### Frontend
*   **Framework:** Flutter
*   **State Management:** Provider
*   **Networking:** `http` package

## ✨ Core Features (MVP)

1.  **Hybrid POI Management:** Seamless toggle between predictive search (Google Places) and manual entry.
2.  **Collaborative Ecosystem:** Real-time JWT-authenticated session sharing for group planning.
3.  **Multimodal Auto-Routing:** AI-driven sequential itinerary generation supporting primary and alternative transportation methods.
4.  **Roulette Mode:** A gamified randomization engine to draw destinations from curated user lists.

## ⚙️ Local Development Setup

### Backend Initialization
\`\`\`bash
cd backend
python -m venv venv
source venv/Scripts/activate  # Windows
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
\`\`\`

### Frontend Initialization
\`\`\`bash
cd frontend
flutter pub get
flutter run
\`\`\`