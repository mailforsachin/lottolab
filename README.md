# 🎲 LottoLab

**LottoLab** is a production-ready statistical analysis, simulation, and optimization platform for lottery games.

## 🚀 Features

- 📊 Data Import: Import historical lottery data (Lotto 6/49, Daily Grand)
- 🔬 Statistical Analysis: Number frequency, randomness tests, pattern analysis
- 🎯 Simulation Engine: Generate millions of tickets and backtest strategies
- 🤖 Strategy Testing: Compare Random, Sobol, Monte Carlo, Genetic Algorithm, and Hybrid AI
- 📈 Interactive Dashboard: Visualize data with charts and graphs
- 🔐 User Authentication: Secure login system
- 📱 REST API: Full API access for programmatic use

## 📊 Supported Games

| Game | Draws | Years | Data Source |
|------|-------|-------|-------------|
| Lotto 6/49 | 4,434 | 1982-2026 | Kaggle / OLG |
| Daily Grand | 1,017 | 2016-2026 | OLG API / Web |

## 🛠️ Technology Stack

### Backend
- FastAPI - Modern Python web framework
- SQLAlchemy 2.x - ORM with Alembic migrations
- MariaDB - Relational database
- Pydantic - Data validation
- NumPy/Pandas - Data processing

### Frontend
- HTML5/CSS3 - Modern responsive design
- Vanilla JavaScript - No frameworks needed
- Chart.js - Interactive visualizations

## 📦 Quick Start

1. Clone and setup:
   git clone https://github.com/yourusername/lottolab.git
   cd lottolab
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt

2. Configure database:
   mysql -u root -p
   CREATE DATABASE lottolab;
   CREATE USER 'lottolab'@'localhost' IDENTIFIED BY 'your_password';
   GRANT ALL PRIVILEGES ON lottolab.* TO 'lottolab'@'localhost';

3. Run migrations and start:
   alembic upgrade head
   python3 -m backend.main

## 🎯 Usage

- Dashboard: https://lottolab.omchat.ovh
- Login: admin / [your_password]
- API Docs: https://lottolab.omchat.ovh/api/docs

## 📝 License

MIT License - See LICENSE file for details

## ⚠️ Disclaimer

LottoLab is for educational purposes only. Lottery is a form of gambling and should be approached responsibly.


## Production Deployment

### Health Check

The application provides a health check endpoint:

`GET /api/health`

### Environment Configuration

Use `.env.example` as the configuration template and keep the real `.env` file out of version control. Configure environment variables according to `backend/config/settings.py`.

### Service

LottoLab runs as a systemd service. Check its status with:

```bash
sudo systemctl status lottolab.service
```

### Database Schema

The required database schema must exist before deployment. Saved portfolio functionality requires these tables:

saved_portfolios
saved_portfolio_tickets
saved_portfolio_allocations

Verify the database schema against the application models before deployment. The repository includes database setup tooling. Verify the appropriate schema-management procedure before applying any production database changes.
