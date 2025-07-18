# Online Cinema

A comprehensive digital platform that allows users to browse, purchase, and manage movie collections. 
This platform provides a complete movie streaming service with user authentication, shopping cart functionality, 
payment processing, and administrative tools.

## Features

### User Features
- **Account Management**: User registration, email verification, password reset
- **Movie Catalog**: Browse movies with pagination, search, filter, and sort functionality
- **Interactive Elements**: Like/dislike movies, write comments, rate movies (1-10 scale)
- **Favorites System**: Add movies to favorites with full catalog functionality
- **Shopping Cart**: Add movies to cart, manage purchases
- **Order Management**: Place orders, view order history, track payment status
- **Notifications**: Email confirmations and notifications

### Admin/Moderator Features
- **Content Management**: CRUD operations for movies, genres, actors, and directors
- **User Management**: Manage user accounts, roles, and permissions
- **Sales Analytics**: View sales data and user behavior
- **Order Monitoring**: Track all orders and payments across the platform

### Technical Features
- **JWT Authentication**: Secure token-based authentication with refresh tokens
- **Payment Integration**: Stripe payment processing with webhook support
- **Role-Based Access Control**: User, Moderator, and Admin roles
- **Database Optimization**: Efficient queries with proper indexing

## Technology Stack

- **Backend**: Python, FastAPI, SQLAlchemy, Alembic, Pydantic
- **Database**: PostgreSQL
- **Authentication**: JWT tokens
- **Payment Processing**: Stripe
- **Task Queue**: Celery with Redis
- **Email Service**: SMTP integration
- **Caching**: Redis

## Database Schema

The application uses a well-structured database with the following main entities:

### Core Entities
- **Users & Authentication**: User profiles, groups, tokens
- **Movies**: Movie catalog with genres, directors, stars, certifications
- **Shopping**: Cart and cart items
- **Orders**: Order management and tracking
- **Payments**: Payment processing and history

### Key Relationships
- Users have profiles and belong to groups (User/Moderator/Admin)
- Movies have many-to-many relationships with genres, directors, and stars
- Users have one cart with multiple cart items
- Orders contain multiple order items and link to payments

## Getting Started

### Prerequisites
- Python 3.10+
- PostgreSQL 12+
- Redis 6+

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/anastmishchuk/online_cinema.git
   cd online_cinema
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Configuration**
   ```bash
   cp .env.example .env
   ```

5. **Database Setup**
   ```bash
   createdb online_cinema
   
   alembic upgrade head

   ```

6. **Start Redis and Celery**
   ```bash
   redis-server
   
   celery -A celery_config.celery_setup worker --loglevel=info
   ```

7. **Run the application**
   ```bash
   cd src
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

## ⚙️ Configuration

### Environment Variables

Create a `.env` file with the following variables:

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/online_cinema

# Security
SECRET_KEY=your-secret-key
JWT_SECRET_KEY=your-jwt-secret-key

# Email Configuration
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# Stripe Configuration
STRIPE_PUBLIC_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Redis
REDIS_URL=redis://localhost:6379/0

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

## 🔐 Authentication & Authorization

### User Roles

- **User**: Basic access to browse and purchase movies
- **Moderator**: Content management and sales analytics
- **Admin**: Full system access including user management

### Token Management

- **Access Token**: Short-lived (30 minutes)
- **Refresh Token**: Long-lived (7 days)
- **Activation Token**: 24 hours validity
- **Password Reset Token**: 1 hour validity

## 🛒 Shopping & Payment Flow

1. **Browse Catalog**: Users explore movies with search/filter options
2. **Add to Cart**: Movies added to personal shopping cart
3. **Create Order**: Cart items converted to order
4. **Payment**: Stripe integration for secure payments
5. **Confirmation**: Email confirmation and order tracking

## 📧 Email System

Automated emails are sent for:
- Account activation
- Password reset
- Order confirmation
- Payment notifications
- Comment replies and likes

## 🔄 Periodic Tasks

Celery Beat handles:
- Expired token cleanup
- Email queue processing
- System maintenance tasks

## 🎯 API Endpoints

### Authentication
- `POST /api/v1/users/register` - User registration
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/refresh` - Token refresh
- `POST /api/v1/auth/logout` - User logout

### Movies
- `GET /api/v1/movies` - List movies with pagination
- `GET /api/v1/movies/{id}` - Movie details
- `POST /api/v1/movies/{id}/like` - Like/unlike movie
- `POST /api/v1/movies/{id}/comments` - Add comment

### Cart & Orders
- `GET /api/v1/cart` - View cart
- `POST /api/v1/movies/{id}/add` - Add movie to cart
- `POST /api/v1/orders` - Create order
- `GET /api/v1/orders` - Order history

### Payments
- `POST /api/v1/payment/` - Create payment
- `POST /api/v1/stripe/webhook` - Stripe webhook

## 🧪 Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/movies/test_movies.py
```

## Deployment

### Docker Deployment

```bash
# Run database migrations first
docker-compose run --rm <your-web-service-name> alembic upgrade head

# Build and start all services
docker-compose up --build -d

# View logs
docker-compose logs -f
```

## API Documentation

- **Interactive API docs**: http://localhost:8000/docs
- **Alternative API docs**: http://localhost:8000/redoc
