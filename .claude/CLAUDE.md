# Pablo's Pizza - Project Overview

## 📋 Protocolo de Inicio de Sesión
### INSTRUCCIONES OBLIGATORIAS PARA CLAUDE:
1. **SIEMPRE lee el archivo `planning.md`** al inicio de cada conversación
2. **Checkea `task.md`** antes de empezar a trabajar en cualquier tarea
3. **Marca como completado** cada tarea inmediatamente después de finalizarla
4. **Agrega nuevas tareas descubiertas** al archivo `task.md` durante el desarrollo

## 🏗️ Project Structure
```
Pablos Pizza/
├── frontend/          # React app with Vite + Material-UI
├── backend/           # Python Flask API + Firebase
├── docs/              # API documentation
└── .claude/           # Claude configuration
    ├── planning.md    # Project vision, architecture, tech stack
    ├── task.md        # Task management and milestones
    └── claude.md      # This file - project overview
```

## 🔗 Related Documentation Files
- **[planning.md](./planning.md)** - Project vision, architecture, technology stack, tools
- **[task.md](./task.md)** - Complete task breakdown by milestones with status tracking
- [Frontend Documentation](./CLAUDE-FRONTEND.md) - React components, routing, state management
- [Backend Documentation](./CLAUDE-BACKEND.md) - API endpoints, database models, business logic
- [API Reference](./docs/API_DOCUMENTATION.md) - Complete API specification

## 🚀 Quick Start Commands
```bash
# Frontend (React + Vite)
cd frontend && npm run dev

# Backend (Python Flask)
cd backend && python main.py

# Firebase deployment
firebase deploy
```

## 🔧 Tech Stack
- **Frontend:** React 18, Material-UI, React Router, Axios
- **Backend:** Python Flask, Firebase Firestore, Firebase Auth
- **Storage:** Firebase Storage
- **Deployment:** Firebase Hosting + Cloud Run

## 📱 Core Features
1. **Public Website** - Booking system, gallery, contact forms
2. **Admin Panel** - Booking management, event tracking, reports
3. **Contact System** - WhatsApp integration, priority handling
4. **Financial Tracking** - Cost analysis, profit calculation
5. **Gallery Management** - Event photos with publication workflow

## 🔄 Recent Changes (Latest Session)
- ✅ Removed all chat functionality completely
- ✅ Implemented new contact system with WhatsApp notifications
- ✅ Enhanced booking workflow with cost editing before completion
- ✅ Fixed gallery photos display issue

## 📊 Current Project Status
- **Version**: v2.0 (post-chat removal)
- **Status**: Production active with continuous improvements
- **Current Milestone**: M1 - Complete Inventory System
- **Next Priority**: Advanced financial reporting

## 🎯 Development Focus Areas
**Before starting any work, always:**
1. Read `planning.md` for project context and architecture
2. Check `task.md` for current milestone and specific tasks
3. Use specific documentation files for detailed work:
   - Frontend components → See CLAUDE-FRONTEND.md
   - API endpoints → See CLAUDE-BACKEND.md
   - Full API spec → See docs/API_DOCUMENTATION.md

## 🏆 Completed Milestones
- ✅ **M0: Core System Development** - Full system operational
  - Public website with booking system
  - Complete admin panel
  - WhatsApp integration
  - Gallery management
  - Financial tracking basics

## 🔄 In Progress
- 🔄 **M1: Complete Inventory System** (Current focus)
  - Backend inventory models and APIs
  - Frontend inventory management
  - Stock alerts and tracking
  - Integration with event costs

## 📋 Upcoming Milestones
- **M2**: Advanced Financial Reports
- **M3**: Performance & Security Optimization  
- **M4**: Mobile Experience Enhancement
- **M5**: Automation & Integration

## 🚀 Key Development Guidelines
1. **Always apply best practices** for both Python and React
2. **Review code** before confirming implementations  
3. **Maintain consistency** with existing architecture
4. **Prioritize performance** and user experience
5. **Document technical decisions** in relevant files
6. **Update task.md** with progress and new discoveries

## 🔍 Quick Reference Links
- **Frontend Dev Server**: http://localhost:3000
- **Backend Dev Server**: http://localhost:5000  
- **Production Frontend**: https://pablospizza.web.app
- **Production Backend**: https://main-4kqeqojbsq-uc.a.run.app
- **Firebase Console**: Console for database and hosting management

---

**Always remember**: This is an active production system serving real customers. Test thoroughly and maintain high code quality standards.