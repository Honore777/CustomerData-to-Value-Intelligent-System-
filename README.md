# 🚀 Supermarket AI Agent - Customer Churn Prediction & Retention

A production-ready MVP for African supermarkets/retail businesses to predict customer churn, identify at-risk customers, and increase retention revenue.

## 📊 What This Does

```
Business uploads CSV/Excel →  Model trains  →  Dashboard shows:
  (sales data)              (Random Forest)   - At-risk customers
                                             - Churned customers
                                             - Revenue at risk
                                             - Top products
                                             - Recommendations
```

## 🎯 Key Features

✅ **CSV/Excel Upload** - Auto-detect and map columns, no manual setup
✅ **Auto Label Engineering** - Generate churn labels based on configurable threshold
✅ **Random Forest Model** - Fast, accurate churn predictions
✅ **Customer Segmentation** - Churned, At-Risk, Active, Loyal
✅ **RFM Analysis** - Recency, Frequency, Monetary value
✅ **Smart Recommendations** - Who to contact & what to offer
✅ **Dashboard** - Beautiful metrics, segments, top products
✅ **Production-Ready Code** - FastAPI + React + TypeScript + PostgreSQL

## 🏗️ Architecture

### Backend (FastAPI)
```
/backend/app/
├── main.py              # FastAPI app + business registration
├── models.py            # SQLAlchemy ORM models
├── schemas.py           # Pydantic request/response schemas
├── database.py          # Database connection & session
├── routers/
│   ├── customers.py     # Customer CRUD
│   ├── transactions.py  # CSV upload & processing
│   └── predictions.py   # ML predictions & insights
└── services/
    ├── ml_pipeline.py   # Random Forest training & prediction
    └── churn_utils.py   # RFM calculation & label engineering
```

### Frontend (React + TypeScript + Zustand + MUI)
```
/frontend/src/
├── pages/
│   ├── Dashboard.tsx         # Main metrics & upload
│   ├── CustomersList.tsx     # Customers by segment
│   └── CustomerDetail.tsx    # Individual customer insights
├── components/
│   ├── CSVUploadDialog.tsx   # File upload with progress
│   └── MetricsCard.tsx       # Reusable metric cards
├── services/
│   └── api.ts                # Axios API calls
└── stores/
    └── dashboardStore.ts     # Zustand state management
```

## 🚀 Quick Start

### 1. Prerequisites

```bash
# Python 3.9+
python --version

# PostgreSQL (or SQLite for local testing)
# Node.js 16+
node --version
```

### 2. Backend Setup

```bash
# Clone & navigate
cd supermarket-ai-agent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy .env and configure database
cp .env.example .env
# Edit .env with your database URL

# Run backend
python -m uvicorn backend.app.main:app --reload
# Backend running on http://localhost:8000
```

### 3. Frontend Setup

```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Create .env file
echo "REACT_APP_API_URL=http://localhost:8000" > .env

# Run frontend
npm start
# Frontend running on http://localhost:3000
```

## 📈 MVP Flow

### Step 1: Register Business
```python
POST /businesses/register
{
  "name": "SuperMart Lagos",
  "email": "owner@supermart.com",
  "phone": "+234123456789",
  "days_inactive_threshold": 30
}
```

### Step 2: Upload Sales Data
```
1. Click "Upload Sales Data" button
2. Select CSV/Excel file (auto-detects columns)
3. Set days_inactive_threshold (e.g., 30 for supermarket)
4. System automatically:
   - Cleans & standardizes data
   - Generates churn labels
   - Trains Random Forest model
   - Generates predictions
   - Stores everything in PostgreSQL
```

### Step 3: View Dashboard
```
- Total customers & revenue
- Revenue at risk
- Segment breakdown (Churned, At-Risk, Active, Loyal)
- Top products
- Click on any customer for details
```

### Step 4: Take Action
```
- View at-risk customers
- See recommended actions (send discount, special offer)
- Click customer to see purchase history & insights
- Plan retention campaigns
```

## 📊 Data Requirements (CSV/Excel)

Minimum columns (will auto-detect):
```
customer_id | purchase_date | amount | product_name
    CUST001 | 2024-01-15    | 5000   | Rice
    CUST002 | 2024-01-20    | 2500   | Oil
```

Optional columns:
```
customer_name | category | quantity
John Doe      | Groceries| 1
Jane Smith    | Groceries| 2
```

## 🧠 ML Model

### Label Engineering
```python
Based on days_inactive_threshold (default 30):

Segment     | Rule
─────────────────────────────────
CHURNED     | days_inactive > 30
AT_RISK     | 25 < days_inactive ≤ 30
ACTIVE      | days_inactive < 15
LOYAL       | high_frequency AND high_monetary
```

### Features
```
- Recency     : Days since last purchase
- Frequency   : Total number of purchases
- Monetary    : Total amount spent
- RF Score    : Combined RFM score
- Velocity    : Purchases per active day
```

### Model
```
Random Forest Classifier
├─ n_estimators: 100
├─ max_depth: 15
├─ class_weight: balanced
└─ Accuracy: ~75-90% (depending on data)
```

## 🔌 API Endpoints

### Businesses
```
POST   /businesses/register                      # Register new business
GET    /businesses/{business_id}                # Get business details
PATCH  /businesses/{business_id}                # Update settings
```

### Transactions
```
POST   /transactions/upload-csv/{business_id}   # Upload & train model
GET    /transactions/{business_id}              # Get transactions
```

### Predictions
```
GET    /predictions/{business_id}/dashboard     # Dashboard metrics
GET    /predictions/{business_id}/segment/{seg} # Get segment customers
GET    /predictions/{business_id}/recommendations # Get recommendations
```

### Customers
```
GET    /customers/{business_id}                 # All customers
GET    /customers/{business_id}/{customer_id}   # Customer detail
```

## 💾 Database Schema

### Businesses
```sql
id | name | email | days_inactive_threshold | created_at
```

### Customers
```sql
id | business_id | customer_id | name | last_purchase_date | total_spent | total_purchases
```

### Transactions
```sql
id | business_id | customer_id_fk | product_name | amount | purchase_date | category
```

### Predictions
```sql
id | business_id | customer_id_fk | segment | churn_probability | recency | frequency | monetary
```

### ModelMetadata
```sql
id | business_id | model_path | training_date | accuracy | num_samples
```

## 🎨 UI Screenshots

### Dashboard
- 📊 Key metrics (Total customers, Revenue, Revenue at risk)
- 📈 Segment breakdown (Churned, At-Risk, Active, Loyal)
- 🔥 Top products table
- 📤 Upload button

### Customers List
- 📋 Tabs for each segment
- 🎯 Customer table with churn risk
- 🔗 Click for details

### Recommendations
- 🚨 High priority (top 10 at-risk)
- ⚠️ Medium priority (upcoming churn)
- 👑 VIP treatment (loyal customers)

## 🚢 Deployment

### Option 1: Railway (Easiest)
```bash
# Backend
railway link
railway up

# Frontend
vercel deploy
```

### Option 2: Heroku + Netlify
```bash
# Backend
git push heroku main

# Frontend  
npm run build
netlify deploy
```

### Option 3: AWS/GCP/Azure
```bash
# Use Docker
docker build -t supermarket-ai-backend .
docker push ...
```

## 🔐 Security Notes

- [ ] Add authentication (JWT tokens)
- [ ] Validate file uploads (size, content)
- [ ] Rate limit API
- [ ] HTTPS in production
- [ ] Encrypt sensitive data
- [ ] SQL injection protection (SQLAlchemy handles this)

## 🧪 Testing

```bash
# Backend tests
pytest backend/

# Coverage
pytest --cov=backend/

# Lint
flake8 backend/
black backend/
```

## 📋 Upcoming Features (Phase 2)

- [ ] WhatsApp alerts (Twilio)
- [ ] Email notifications
- [ ] Automated discount campaigns
- [ ] Multiple user roles (owner, sales manager, admin)
- [ ] Advanced charts & trends
- [ ] Predictive revenue impact
- [ ] A/B testing for campaigns
- [ ] Multi-language support

## 💰 Monetization

**Tier 1: Starter ($15/month)**
- 1 store
- Monthly upload
- Basic dashboard

**Tier 2: Growth ($35/month)**
- 1 store
- Weekly upload
- Advanced analytics

**Tier 3: Enterprise ($75+/month)**
- Multiple stores
- Real-time sync
- API access
- White-label option

## 📞 Support

- Email: support@supermarket-ai.com
- Issues: GitHub issues
- Docs: /docs (Swagger UI)

## 📄 License

MIT License - See LICENSE file

## 🙏 Contributing

Contributions welcome! Please:
1. Fork repository
2. Create feature branch
3. Submit pull request

---

**Built for African businesses. Built by developers who care.** 🌍
