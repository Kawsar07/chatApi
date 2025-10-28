# ChatApp – Private Messaging with Profile Picture & Location

A **secure, real-time-ready private chat application** with **Push Notifications**, built using:

- **Backend**: Python + Django + Django REST Framework  
- **Database**: **PostgreSQL** (Production-ready)  
- **Frontend**: **Flutter** (Android & iOS)  
- **Authentication**: Token + Firebase FCM Push Notifications  

---
## Features
| Feature | Status |
|-------|--------|
| Register with **Profile Picture & Location** | Done |
| Login (email or username) | Done |
| Search & Add Friends | Done |
| Send/Receive Messages | Done |
| **Push Notifications** (New message) | Done |
| **Unread Message Count** | Done |
| Total Friends & Messages Count | Done |
| Update Profile | Done |
| **Flutter Mobile App** | Done |
| **PostgreSQL Database** | Done |
---
## Mobile App Screenshots (Flutter)

| Screen                  | Preview 1                                      | Preview 2                                      |
|-------------------------|------------------------------------------------|------------------------------------------------|
| **Login / Register**    | <img src="https://github.com/Kawsar07/chatApi/blob/main/chat/screenshorts/login.png?raw=true" width="250"/> | <img src="https://github.com/Kawsar07/chatApi/blob/main/chat/screenshorts/regestion.png?raw=true" width="250"/> |
| **Friends List / Chat** | <img src="https://github.com/Kawsar07/chatApi/blob/main/chat/screenshorts/all_user.png?raw=true" width="250"/> | <img src="https://github.com/Kawsar07/chatApi/blob/main/chat/screenshorts/chat.png?raw=true" width="250"/> |
| **Profile / Notification** | <img src="https://github.com/Kawsar07/chatApi/blob/main/chat/screenshorts/profile.png?raw=true" width="250"/> | <img src="https://github.com/Kawsar07/chatApi/blob/main/chat/screenshorts/notification.png?raw=true" width="250"/> |

---
## API Endpoints (Full Documentation)

| Method | Endpoint | Description | Auth |
|--------|---------|-------------|------|
| `POST` | `/api/register/` | Register with picture & location | No |
| `POST` | `/api/login/` | Login → get token | No |
| `GET` | `/api/users/?search=john` | Search users | Yes |
| `POST` | `/api/add-friend/` | Send friend request | Yes |
| `GET` | `/api/friends/` | List all friends | Yes |
| `GET` | `/api/friend-requests/?type=received` | List friend requests | Yes |
| `GET` | `/api/friend-requests/?type=sent` | List sent requests | Yes |
| `POST` | `/api/friend-request/action/` | Accept/Reject request | Yes |
| `GET` | `/api/messages/<username>/` | Get chat history | Yes |
| `GET` | `/api/messages/count/` | Unread count per friend | Yes |
| `GET` | `/api/message-count/` | **Total messages (sent + received)** | Yes |
| `GET` | `/api/friend-count/` | **Total friends count** | Yes |
| `GET` | `/api/profile/` | Get own profile | Yes |
| `PUT` | `/api/profile/update/` | Update profile | Yes |

## Project Structure

```text
chatapp/
├── chat/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── models.py
│   ├── views.py
│   ├── serializers.py
│   ├── urls.py
│   └── tests.py
├── media/
│   └── profiles/             
├── chatapp/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── manage.py
├── requirements.txt
├── README.md
└── .gitignore
