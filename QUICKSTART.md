# 🎯 QUICK START GUIDE - GET RUNNING IN 30 MINUTES

## What You Have

A complete, production-ready MVP with:
- ✅ FastAPI backend with ML pipeline
- ✅ React frontend with Zustand store
- ✅ PostgreSQL database schema
- ✅ CSV upload & auto-training
- ✅ Customer segmentation
- ✅ Professional UI dashboard

## 30-Minute Setup

### 1. Backend (15 minutes)

```bash
# Navigate to project
cd supermarket-ai-agent

# Create Python environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env

# Edit .env - choose one:
# Option A (SQLite - local testing, NO SETUP NEEDED):
DATABASE_URL=sqlite:///./test.db

# Option B (PostgreSQL - need to install):
DATABASE_URL=postgresql://postgres:password@localhost:5432/supermarket_mvp

# Start backend
python -m uvicorn backend.app.main:app --reload
```

✅ Backend running on http://localhost:8000
- Check health: http://localhost:8000/
- API docs: http://localhost:8000/docs

### 2. Frontend (10 minutes)

```bash
# In new terminal
cd frontend

# Install dependencies
npm install

# Create .env
echo "REACT_APP_API_URL=http://localhost:8000" > .env

# Start frontend
npm start
```

✅ Frontend running on http://localhost:3000

---

## 🧪 Test It Now

### 1. Register a Business
```bash
# In browser or curl
POST http://localhost:8000/businesses/register
Body:
{
  "name": "My Supermarket",
  "email": "owner@supermarket.com",
  "days_inactive_threshold": 30
}

# Response: {"id": 1, "name": "My Supermarket", ...}
# Save the business_id (1 in this case)
```

### 2. Create Sample Data
```bash
# In Python (create test_data.py):
import pandas as pd
from datetime import datetime, timedelta
import random

# Generate sample data
customers = [f"CUST{i:03d}" for i in range(1, 51)]
products = ["Rice", "Oil", "Beans", "Flour", "Sugar", "Salt"]

data = []
base_date = datetime.now()

for customer in customers:
    # Random number of transactions
    num_transactions = random.randint(5, 50)
    
    for _ in range(num_transactions):
        days_ago = random.randint(0, 60)
        data.append({
            "customer_id": customer,
            "purchase_date": (base_date - timedelta(days=days_ago)).strftime("%Y-%m-%d"),
            "amount": random.uniform(1000, 10000),
            "quantity": random.randint(1, 5),
            "product_name": random.choice(products)
        })

df = pd.DataFrame(data)
df.to_csv("sample_data.csv", index=False)
print(f"Created {len(df)} transactions for {len(customers)} customers")
```

### 3. Upload CSV

Go to http://localhost:3000:
1. Dashboard will prompt upload
2. Click "Upload Sales Data"
3. Select sample_data.csv
4. Set threshold: 30 days
5. Click "Upload & Train"
6. Wait for model training (~3-5 seconds)

### 4. View Results

After upload:
- ✅ See dashboard with metrics
- ✅ View customers by segment
- ✅ Click customer for details
- ✅ See recommendations

---

## 📁 Project Structure

```
supermarket-ai-agent/
├── backend/
│   └── app/
│       ├── main.py           # Start here
│       ├── models.py         # Database models
│       ├── schemas.py        # Data validation
│       ├── routers/          # API endpoints
│       │   ├── customers.py
│       │   ├── transactions.py  # CSV upload
│       │   └── predictions.py   # ML results
│       └── services/
│           ├── ml_pipeline.py   # Random Forest
│           └── churn_utils.py   # RFM + labels
├── frontend/
│   └── src/
│       ├── pages/            # Dashboard, Lists
│       ├── components/       # Upload dialog, Metrics
│       ├── services/         # API calls
│       └── stores/           # Zustand state
├── requirements.txt          # Python packages
└── README.md                 # Full docs
```

---

## 🔑 Key Files to Understand

### 1. Backend Flow

**CSV Upload** → `routers/transactions.py:upload_csv()`
- Reads CSV
- Maps columns
- Stores transactions
- Calls ML pipeline

**ML Pipeline** → `services/ml_pipeline.py`
- `train_random_forest()` - Train model
- `predict_churn()` - Make predictions

**Churn Labels** → `services/churn_utils.py`
- `calculate_rfm_metrics()` - RFM calculation
- `generate_churn_labels()` - Create labels
- `generate_recommendations()` - Smart suggestions

**Results** → `routers/predictions.py`
- `/dashboard` - Metrics & insights
- `/segment/{type}` - Customers by segment
- `/recommendations` - Actions to take

### 2. Frontend Flow

**Store** → `stores/dashboardStore.ts` (Zustand)
- Manages: businessId, predictions, UI state
- Persisted to localStorage

**API** → `services/api.ts` (Axios)
- All calls to FastAPI backend
- Error handling

**Pages** → `pages/Dashboard.tsx`, `CustomersList.tsx`
- Display data from store
- Call API services
- Update store on success

---

## 🚀 What to Do Next

### Week 1: MVP Validation
- [ ] Test with real supermarket data
- [ ] Get feedback on UI
- [ ] Fix any bugs
- [ ] Create sample CSV templates

### Week 2: Deployment
- [ ] Deploy backend (Railway, Heroku, AWS)
- [ ] Deploy frontend (Vercel, Netlify)
- [ ] Custom domain
- [ ] SSL certificate

### Week 3: Sales
- [ ] Create landing page
- [ ] Email 10 supermarkets
- [ ] Demo + get feedback
- [ ] Close first 3 customers

### Phase 2: Add Features
- [ ] WhatsApp alerts (Twilio)
- [ ] Email campaigns
- [ ] User authentication
- [ ] Multi-store support
- [ ] Advanced analytics

---

## 🐛 Common Issues

### Backend won't start
```
Error: ModuleNotFoundError
Fix: pip install -r requirements.txt
```

### Frontend can't connect to backend
```
Error: CORS error
Fix: Check REACT_APP_API_URL in .env
```

### Database error
```
Error: fe_sendauth: no password supplied
Fix: Check DATABASE_URL in .env
```

### Model training takes too long
```
Normal: First upload takes 3-5 seconds
Fix: Reduce tree depth in ml_pipeline.py
```

---

## 💡 Pro Tips

1. **Test locally first** - Use SQLite for testing
2. **Start with small CSVs** - 100 transactions = fast testing
3. **Monitor logs** - Watch console for errors
4. **Save API responses** - Useful for debugging
5. **Version control** - Commit before major changes

---

## 🎯 Next Steps

1. ✅ Get backend & frontend running
2. ✅ Test with sample data
3. ✅ Deploy to production
4. ✅ Get first paying customers
5. ✅ Iterate based on feedback

**You've got this! 🚀**

Questions? Check README.md or reach out to the community.
