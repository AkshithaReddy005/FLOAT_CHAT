# FloatChat - ARGO Data System

FloatChat is a web application for analyzing and visualizing ARGO oceanographic data using AI-powered search and analysis capabilities.

## Quick Start

Want to get up and running quickly? Follow these steps:

1. **Check Prerequisites**: `python scripts/check_setup.py`
2. **Setup Environment**: Copy `.env.example` files and configure
3. **Install Dependencies**: Install Python packages and Node.js modules
4. **Setup Database**: Run the database setup script
5. **Start Servers**: Launch both backend and frontend

Detailed instructions below:


## Prerequisites

Before setting up the project, ensure you have the following installed:

- **Node.js** (v18 or higher) - [Download here](https://nodejs.org/)
- **Python** (v3.8 or higher) - [Download here](https://python.org/)
- **PostgreSQL** (v12 or higher) - [Download here](https://postgresql.org/download/)

## Setup Instructions

### 1. Clone the Repository

```bash
git clone <repository-url>
cd floatchat
```

### 2. Set Up Environment Variables

#### Server Environment Variables
```bash
# Navigate to server directory
cd apps/server

# Copy the environment template
cp .env.example .env

# Edit the .env file with your PostgreSQL credentials
# Update the following variables:
# DB_PASSWORD=your_actual_postgresql_password
# DB_USER=your_postgresql_username (default: postgres)
```

#### Client Environment Variables
```bash
# Navigate to client directory
cd ../client

# Copy the environment template
cp .env.example .env

# The default values should work for local development
```

### 3. Set Up PostgreSQL Database

1. **Install PostgreSQL** if you haven't already
2. **Start PostgreSQL service**
   - Windows: PostgreSQL should start automatically after installation
   - macOS: `brew services start postgresql`
   - Linux: `sudo systemctl start postgresql`

3. **Create a PostgreSQL user** (if needed):
   ```sql
   -- Connect to PostgreSQL as superuser
   psql -U postgres
   
   -- Create a new user (optional, you can use 'postgres' user)
   CREATE USER your_username WITH PASSWORD 'your_password';
   ALTER USER your_username CREATEDB;
   ```

4. **Update your server .env file** with the correct database credentials:
   ```bash
   DB_HOST=localhost
   DB_PORT=5432
   DB_USER=postgres  # or your created username
   DB_PASSWORD=your_actual_password
   DB_NAME=floatchat
   ```

### 4. Set Up the Backend (Server)

```bash
# Navigate to server directory
cd apps/server

# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Set up the database (this will create the database and tables)
python setup_db.py

# Start the FastAPI server
python src/main.py
```

The server will start at `http://localhost:8000`

### 5. Set Up the Frontend (Client)

```bash
# Open a new terminal and navigate to client directory
cd apps/client

# Install Node.js dependencies
npm install

# Start the development server
npm run dev
```

The client will start at `http://localhost:3000`

## Verification

### Check if everything is working:

Run the setup verification script:
```bash
python scripts/check_setup.py
```

This will check:
- Python and Node.js versions
- Required Python packages
- PostgreSQL availability
- Environment file configuration

### Manual Verification:

1. **Database**: Run `python setup_db.py` in the server directory - you should see:
   ```
   === FloatChat Database Setup ===
   Connecting to PostgreSQL at localhost:5432 as user 'postgres'
   Target database: floatchat
   ✅ Connected to PostgreSQL: PostgreSQL 14.x...
   Database 'floatchat' already exists.
   Creating tables and indexes...
   Tables created successfully!
   ✅ Database setup completed successfully!
   ```

2. **Backend**: Visit `http://localhost:8000/docs` to see the FastAPI documentation

3. **Frontend**: Visit `http://localhost:3000` to see the React application

## Development Workflow

### Starting the Application

1. **Start PostgreSQL** (if not already running)
2. **Start the backend**:
   ```bash
   cd apps/server
   # Activate virtual environment if not active
   venv\Scripts\activate  # Windows
   # source venv/bin/activate  # macOS/Linux
   python src/main.py
   ```

3. **Start the frontend** (in a new terminal):
   ```bash
   cd apps/client
   npm run dev
   ```

### Making Changes

- **Backend changes**: The FastAPI server will auto-reload when you save files
- **Frontend changes**: The Vite dev server will hot-reload when you save files
- **Database schema changes**: Update the schema in `setup_db.py` and run it again

## Project Features

- **File Upload**: Upload NetCDF ARGO data files
- **AI Search**: Query the data using natural language
- **Data Visualization**: Interactive charts and maps
- **Vector Search**: Semantic search capabilities using ChromaDB
- **Admin Dashboard**: Manage uploaded files and system status

## Troubleshooting

### Common Issues

1. **PostgreSQL Connection Error**:
   - Ensure PostgreSQL is running
   - Check your database credentials in `.env`
   - Verify the database exists by running `setup_db.py`

2. **Python Package Errors**:
   - Make sure you're using the virtual environment
   - Try upgrading pip: `pip install --upgrade pip`
   - Reinstall requirements: `pip install -r requirements.txt`

3. **Node.js Issues**:
   - Delete `node_modules` and run `npm install` again
   - Check Node.js version: `node --version` (should be v18+)

4. **Port Already in Use**:
   - Backend: Change `BACKEND_PORT` in server `.env`
   - Frontend: Change `FRONTEND_PORT` in client `.env`

### Environment Variables Reference

#### Server (.env)
```bash
# Database Configuration
DB_HOST=localhost                    # PostgreSQL host
DB_PORT=5432                        # PostgreSQL port
DB_USER=postgres                    # PostgreSQL username
DB_PASSWORD=your_password_here      # PostgreSQL password
DB_NAME=floatchat                   # Database name

# Server Configuration  
BACKEND_HOST=127.0.0.1             # Backend server host
BACKEND_PORT=8000                  # Backend server port

# Vector Store
CHROMA_PERSIST_DIR=./chroma_data   # ChromaDB data directory
```

#### Client (.env)
```bash
VITE_API_BASE_URL=http://localhost:8000  # Backend API URL
VITE_FRONTEND_PORT=3000                  # Frontend port
```
