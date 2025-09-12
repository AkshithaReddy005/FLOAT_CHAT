# FloatChat - Advanced ARGO Oceanographic Data Analysis System

FloatChat is a sophisticated web application that combines AI tech with oceanographic data analysis to provide researchers, scientists, and marine professionals with powerful tools for analyzing ARGO float data. The system features an intelligent RAG (Retrieval-Augmented Generation) pipeline, advanced visualization capabilities, and natural language querying.

## **System Overview**

FloatChat transforms complex oceanographic data analysis through:
- **AI-Powered Natural Language Queries**: Ask questions in plain English about oceanographic data
- **Intelligent Visualization Selection**: Automated chart recommendation based on data patterns and query intent
- **Advanced RAG Pipeline**: Context-aware responses using vector embeddings and LLM integration
- **Professional Data Management**: Enterprise-grade data processing and storage capabilities
- **Interactive Visualizations**: Dynamic charts, maps, and depth profiles with intelligent hover interactions

---

## **Comprehensive Feature Documentation**

### **AI & Machine Learning Core**

#### **Advanced RAG (Retrieval-Augmented Generation) System**
- **Multi-Modal RAG Pipeline**: Combines vector search, SQL generation, and LLM responses
- **Gemini AI Integration**: Uses Google's Gemini 2.0 Flash for intelligent query processing
- **Context-Aware Responses**: Maintains conversation history and session context
- **Semantic Search**: ChromaDB-powered vector embeddings for intelligent data retrieval
- **Query Classification Engine**: Automatically categorizes queries by complexity, intent, and data requirements

#### **Intelligent Query Processing**
- **Natural Language to SQL**: Converts complex English queries to optimized SQL
- **Smart Query Classification**: Identifies temporal, spatial, analytical, and visualization intent
- **Chart Request Detection**: Automatically recognizes when users want specific visualizations
- **Context Preservation**: Maintains conversation flow and user preferences across sessions
- **Fallback Mechanisms**: Graceful degradation when AI services are unavailable

#### **Advanced Scoring & Selection Algorithms**
- **Visualization Relevance Scoring**: Multi-factor algorithm (0.0-2.0+ scale) for chart selection
  - Data quality assessment
  - Query intent matching
  - Geographic/temporal pattern recognition
  - Context relevance calculations
- **Dynamic Chart Prioritization**: Automatically selects primary and secondary visualizations
- **Data Quality Scoring**: Comprehensive assessment of data completeness and reliability

#### **Smart Example Generation**
- **Dynamic Query Suggestions**: AI-generated examples based on actual data availability
- **Context-Aware Examples**: Adapts suggestions to current data patterns and user interests
- **Multi-Complexity Examples**: Simple, analytical, temporal, and spatial query categories

### **Advanced Data Processing & Management**

#### **Robust NetCDF Processing**
- **Multi-Format Support**: Handles various ARGO NetCDF file structures and formats
- **Intelligent Variable Detection**: Automatically maps different naming conventions
- **XArray Integration**: Advanced scientific data processing with pandas and numpy
- **Data Validation**: Comprehensive quality checks and error handling
- **Measurement Extraction**: Processes temperature, salinity, pressure, and geospatial data

#### **Enterprise-Grade Database Management**
- **PostgreSQL Backend**: Optimized for large-scale oceanographic datasets
- **Advanced Indexing**: Multi-column indexes for fast spatial and temporal queries
- **Duplicate Prevention**: SHA-256 hashing with multiple validation layers
- **Batch Processing**: Efficient bulk data operations with transaction management
- **Data Integrity**: Unique constraints and referential integrity enforcement

#### **Comprehensive Duplicate Detection**
- **Multi-Level Validation**: File-level, measurement-level, and batch-level duplicate detection
- **SHA-256 Fingerprinting**: Cryptographic hashing for reliable duplicate identification
- **Intelligent Deduplication**: Preserves data quality while preventing storage bloat
- **Real-Time Monitoring**: Live duplicate detection during file uploads

#### **Advanced Vector Store (ChromaDB)**
- **Semantic Embeddings**: Rich contextual representations of oceanographic measurements
- **Oceanographic Feature Detection**: Recognizes upwelling zones, thermoclines, water masses
- **Analytics-Enhanced Embeddings**: Temperature ranges, salinity patterns, depth categories
- **Persistent Storage**: Maintains embeddings across application restarts
- **Batch Operations**: Efficient vector operations for large datasets

### **Sophisticated Visualization Engine**

#### **Intelligent Chart Selection System**
- **Multi-Factor Scoring Algorithm**: Considers data patterns, query intent, and visualization effectiveness
- **Dynamic Chart Types**:
  - **Interactive Ocean Maps**: Leaflet-based with depth-coded markers and geographic clustering
  - **Advanced Depth Profiles**: Dual-axis temperature/salinity plots with professional styling
  - **Custom Chart Generation**: AI-powered Plotly chart creation based on user requests
  - **Statistical Dashboards**: Automated summary statistics and data distributions

#### **Smart Visualization Features**
- **Collapsible Interface**: Clean UX with data-driven expand/collapse behavior
- **Professional Hover Interactions**: Rich tooltips with formatted data display
- **Responsive Design**: Adaptive layouts for different screen sizes and data volumes
- **Export Capabilities**: High-resolution PNG export with customizable dimensions
- **Real-Time Updates**: Dynamic chart updates based on query refinements

#### **Advanced Chart Request Processing**
- **AI-Powered Chart Generation**: Gemini integration for complex chart creation
- **Natural Language Chart Requests**: "Show me temperature vs depth" → Custom Plotly visualization
- **Intelligent Parameter Mapping**: Automatic axis selection and data transformation
- **Chart Type Recognition**: Identifies scatter, line, histogram, bar, and time series requests
- **Fallback Processing**: Rule-based chart generation when AI is unavailable

### **Professional Frontend Architecture**

#### **Modern React Application**
- **TypeScript Implementation**: Type-safe development with comprehensive interfaces
- **Component-Based Architecture**: Modular, reusable UI components
- **State Management**: Efficient data flow and application state handling
- **Error Boundaries**: Graceful error handling and user feedback

#### **Advanced UI Components**
- **Real-Time Chat Interface**: WebSocket-style conversation flow with typing indicators
- **Professional Admin Dashboard**: Comprehensive system management and monitoring
- **Researcher Tools**: Specialized interfaces for data exploration and analysis
- **File Upload System**: Drag-and-drop NetCDF file handling with progress tracking
- **Interactive Data Grids**: Sortable, filterable data tables with pagination

#### **User Experience Features**
- **Session Context Management**: Maintains conversation state and user preferences
- **Loading States**: Sophisticated loading indicators and skeleton screens
- **Error Handling**: User-friendly error messages with actionable suggestions
- **Responsive Design**: Mobile-optimized layouts and touch-friendly interactions
- **Accessibility**: ARIA labels, keyboard navigation, and screen reader support

### **Backend API Architecture**

#### **FastAPI RESTful Services**
- **Comprehensive API Endpoints**: 15+ specialized endpoints for different functionalities
- **Automatic Documentation**: Interactive Swagger/OpenAPI documentation
- **CORS Configuration**: Secure cross-origin resource sharing
- **Request Validation**: Pydantic models for data validation and serialization
- **Error Handling**: Comprehensive HTTP status codes and error messages

#### **Key API Endpoints**
- **Chat Interface**: `/chat` - Natural language query processing
- **File Management**: `/admin/upload`, `/admin/upload-multiple` - NetCDF file processing
- **Data Retrieval**: `/researcher/query` - Direct data access and filtering
- **System Health**: `/health`, `/admin/stats` - System monitoring and diagnostics
- **Knowledge Base**: `/admin/knowledge-base` - Vector store analytics and insights
- **Database Management**: Multiple endpoints for data management and cleanup

#### **Advanced Security & Validation**
- **SQL Injection Prevention**: Parameterized queries and input sanitization
- **File Validation**: Comprehensive NetCDF format verification
- **Rate Limiting**: Protection against abuse and resource exhaustion
- **Input Sanitization**: Multi-layer validation for all user inputs
- **Error Logging**: Comprehensive logging for debugging and monitoring

### **Analytics & Monitoring Features**

#### **System Health Monitoring**
- **Real-Time Statistics**: Live metrics on data volume, storage usage, and system performance
- **Database Analytics**: Detailed insights into data distribution and quality
- **Vector Store Metrics**: ChromaDB collection statistics and embedding quality
- **Performance Monitoring**: Query response times and system resource usage

#### **Knowledge Base Analytics**
- **Data Distribution Analysis**: Geographic, temporal, and parameter coverage insights
- **RAG System Insights**: Vector similarity analysis and retrieval quality metrics
- **Query Pattern Analysis**: Understanding user behavior and common query types
- **Balance Testing**: Automated testing of data representativeness and coverage

#### **Administrative Tools**
- **Bulk Operations**: Multi-file upload and batch processing capabilities
- **Data Cleanup**: Automated and manual data purging options
- **System Reinitialization**: Complete system reset and reconfiguration
- **File Management**: Detailed tracking of uploaded files and processing status

### **Data Quality & Reliability**

#### **Comprehensive Data Validation**
- **Multi-Level Quality Checks**: File, measurement, and batch-level validation
- **Oceanographic Range Validation**: Realistic value ranges for temperature, salinity, pressure
- **Geographic Validation**: Coordinate system verification and bounds checking
- **Temporal Validation**: Date format standardization and chronological ordering

#### **Advanced Error Handling**
- **Graceful Degradation**: System continues operation during partial failures
- **User-Friendly Error Messages**: Clear explanations with actionable solutions
- **Automatic Recovery**: Self-healing mechanisms for common issues
- **Comprehensive Logging**: Detailed error tracking for debugging and improvement

### **Performance Optimizations**

#### **Database Performance**
- **Strategic Indexing**: Optimized for common query patterns (spatial, temporal, float-based)
- **Query Optimization**: Efficient SQL generation with proper JOIN strategies
- **Connection Pooling**: Managed database connections for high concurrency
- **Bulk Operations**: Batch processing for large data uploads

#### **Frontend Performance**
- **Code Splitting**: Lazy loading of components and modules
- **Memoization**: React optimization for expensive computations
- **Virtual Scrolling**: Efficient rendering of large data sets
- **Progressive Loading**: Staged data loading for better user experience

---

## **Use Cases & Applications**

### **Research Applications**
- **Climate Studies**: Long-term temperature and salinity trend analysis
- **Oceanographic Research**: Water mass identification and tracking
- **Marine Biology**: Habitat characterization and species distribution modeling
- **Coastal Management**: Near-shore environmental monitoring

### **Educational Use**
- **Oceanography Courses**: Interactive data exploration and visualization
- **Data Science Training**: Real-world datasets for machine learning applications
- **Research Methods**: Teaching modern data analysis techniques

### **Professional Applications**
- **Environmental Consulting**: Marine impact assessments and monitoring
- **Government Agencies**: Policy-making support and regulatory compliance
- **Maritime Operations**: Route planning and environmental awareness

---

## **Technical Specifications**

### **Architecture Stack**
- **Backend**: Python 3.8+, FastAPI, SQLAlchemy, PostgreSQL
- **AI/ML**: Google Gemini API, ChromaDB, NumPy, Pandas, XArray
- **Frontend**: React 18+, TypeScript, Tailwind CSS, Vite
- **Visualization**: Plotly.js, Leaflet, D3.js components
- **Data Processing**: NetCDF4, Scientific Python ecosystem

### **Performance Characteristics**
- **Data Capacity**: Handles millions of measurements efficiently
- **Query Response**: Sub-second response times for most queries
- **Concurrent Users**: Designed for multi-user research environments
- **Storage Efficiency**: Optimized data structures and compression

### **Scalability Features**
- **Horizontal Scaling**: Database and API tier scaling capabilities
- **Microservice Ready**: Modular architecture for cloud deployment
- **Container Support**: Docker-ready for modern deployment workflows
- **Cloud Compatible**: AWS, Azure, GCP deployment patterns

---

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
