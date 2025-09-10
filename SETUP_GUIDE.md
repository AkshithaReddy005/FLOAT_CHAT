# FloatChat - Complete Setup Guide

## 🚀 Quick Start (5 Minutes)

### Prerequisites Check
```bash
# Check if you have required software
python --version    # Should be 3.8+
node --version      # Should be 18+
psql --version      # PostgreSQL should be installed
```

---

## 📋 Step-by-Step Setup

### 1. Database Setup (PostgreSQL)

#### Install PostgreSQL (if not installed)
- **Windows**: Download from [postgresql.org](https://www.postgresql.org/download/windows/)
- **During installation**: Remember the password you set for `postgres` user

#### Create Environment File
```bash
# Navigate to server directory
cd c:\Users\akshi\Downloads\elite_hackers_2.0\flowchat\apps\server

# Create .env file
echo DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/floatchat > .env
echo CHROMA_PERSIST_DIR=./chroma_data >> .env
echo BACKEND_HOST=127.0.0.1 >> .env
echo BACKEND_PORT=8000 >> .env
```

**Replace `YOUR_PASSWORD` with your actual PostgreSQL password!**

#### Setup Database
```bash
# Still in server directory
python setup_db.py
```

**Expected Output:**
```
=== FloatChat Database Setup ===
Connected to PostgreSQL: PostgreSQL 14.x...
Database 'floatchat' created successfully!
Tables created successfully!
✓ Database setup completed successfully!
```

### 2. Backend Setup (Already Done ✅)

Your Python dependencies are already installed! Just start the server:

```bash
# In server directory: c:\Users\akshi\Downloads\elite_hackers_2.0\flowchat\apps\server
python src/main.py
```

**Expected Output:**
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000
```

**Keep this terminal open!**

### 3. Frontend Setup

Open a **NEW terminal** and run:

```bash
# Navigate to client directory
cd c:\Users\akshi\Downloads\elite_hackers_2.0\flowchat\apps\client

# Install Node.js dependencies
npm install

# Start development server
npm run dev
```

**Expected Output:**
```
  VITE v7.1.2  ready in 1234 ms

  ➜  Local:   http://localhost:3000/
  ➜  Network: use --host to expose
```

---

## 🎯 Testing Your Setup

### 1. Backend API Test
Open browser: `http://localhost:8000/docs`
- You should see FastAPI documentation
- Try the `/` endpoint - should return: `{"message": "FloatChat ARGO Data System API"}`

### 2. Frontend Test  
Open browser: `http://localhost:3000`
- You should see the FloatChat login screen
- Try both "Admin" and "Researcher" buttons

### 3. Full System Test
1. Click "Admin" → Should show upload interface
2. Click "Researcher" → Should show query interface
3. Try uploading a test file from `c:\Users\akshi\Downloads\elite_hackers_2.0\flowchat\test\`

---

## 🔧 Environment Files Reference

### Server `.env` (Required)
```bash
# c:\Users\akshi\Downloads\elite_hackers_2.0\flowchat\apps\server\.env
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/floatchat
CHROMA_PERSIST_DIR=./chroma_data
BACKEND_HOST=127.0.0.1
BACKEND_PORT=8000
FRONTEND_HOST=localhost
FRONTEND_PORT=3000
```

### Client `.env` (Optional)
```bash
# c:\Users\akshi\Downloads\elite_hackers_2.0\flowchat\apps\client\.env
VITE_API_BASE_URL=http://localhost:8000
VITE_FRONTEND_PORT=3000
```

---

## 🚨 Common Issues & Solutions

### Issue 1: PostgreSQL Connection Failed
```
Error: could not connect to server
```
**Solution:**
```bash
# Check if PostgreSQL is running
# Windows: Check Services or run:
pg_ctl status

# If not running, start it:
# Windows: Start PostgreSQL service from Services panel
```

### Issue 2: Database Authentication Failed
```
Error: authentication failed for user "postgres"
```
**Solution:**
- Double-check your password in `.env` file
- Try connecting manually: `psql -U postgres -h localhost`

### Issue 3: Port Already in Use
```
Error: [Errno 10048] Only one usage of each socket address
```
**Solution:**
```bash
# Find what's using the port
netstat -ano | findstr :8000

# Kill the process (replace PID with actual number)
taskkill /PID 1234 /F
```

### Issue 4: Node.js Dependencies Failed
```
Error: npm ERR! peer dep missing
```
**Solution:**
```bash
# Clear npm cache and reinstall
npm cache clean --force
rm -rf node_modules package-lock.json
npm install
```

### Issue 5: ChromaDB Permission Error
```
Error: Permission denied: './chroma_data'
```
**Solution:**
```bash
# Create directory manually
mkdir chroma_data
# Or run as administrator
```

---

## 🎮 Development Workflow

### Daily Development Startup
```bash
# Terminal 1: Backend
cd c:\Users\akshi\Downloads\elite_hackers_2.0\flowchat\apps\server
python src/main.py

# Terminal 2: Frontend  
cd c:\Users\akshi\Downloads\elite_hackers_2.0\flowchat\apps\client
npm run dev
```

### Making Changes
- **Backend changes**: Server auto-reloads when you save Python files
- **Frontend changes**: Browser auto-refreshes when you save React files
- **Database changes**: Re-run `python setup_db.py`

### Testing with Sample Data
```bash
# Upload test files from:
c:\Users\akshi\Downloads\elite_hackers_2.0\flowchat\test\
# Files: test_arabian_sea_argo.nc, test_bay_of_bengal_argo.nc, etc.
```

---

## 🏆 Verification Checklist

- [ ] PostgreSQL installed and running
- [ ] Backend server starts without errors (`http://localhost:8000/docs` works)
- [ ] Frontend server starts without errors (`http://localhost:3000` works)
- [ ] Can access admin dashboard
- [ ] Can access researcher dashboard  
- [ ] Database tables created (check with: `psql -U postgres -d floatchat -c "\dt"`)
- [ ] Can upload a test NetCDF file
- [ ] Can query uploaded data

---

## 🚀 Ready for Smart India Hackathon!

Once everything is working:

1. **Demo Flow**: Admin uploads → Researcher queries → Show results
2. **Key Features**: 
   - Natural language search: *"Show temperature data from Arabian Sea"*
   - Duplicate detection: Upload same file twice
   - Real-time processing: Data immediately searchable
3. **Technical Highlights**: 
   - Dual database architecture (PostgreSQL + ChromaDB)
   - Advanced RAG implementation
   - Enterprise-level error handling

Your FloatChat system is now ready to impress the judges! 🎯
