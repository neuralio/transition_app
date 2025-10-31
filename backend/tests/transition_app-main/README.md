# Project Setup Instructions

## Local Development Setup

1. **Configure Docker Compose**
   ```bash
   cp docker-compose.yml_local docker-compose.yml
   ```

2. **Configure Nginx**
   ```bash
   cp nginx/nginx.conf_local nginx/nginx.conf
   ```

3. **Configure Frontend (Vite)**
   ```bash
   cp frontend/esa-chat-ui/vite.config_local.js frontend/esa-chat-ui/vite.config.js
   ```

4. **Configure Frontend Environment**
   ```bash
   cp frontend/esa-chat-ui/.env-example frontend/esa-chat-ui/.env
   # Edit frontend/esa-chat-ui/.env and fill in the required values:
   # VITE_BACKEND_BASE_URL=your_backend_url_here
   # VITE_WMS_BASE_URL=your_wms_url_here
   ```

5. **Configure Backend Environment**
   ```bash
   cp backend/.env-example backend/.env
   # Edit backend/.env and fill in the required values:
   # API_KEY=your_api_key_here
   # AGENT_ID=your_agent_id_here
   # REDIS_HOST=your_redis_host_here
   ```

6. **Configure Global Environment**
   ```bash
   cp .env-example .env
   # Edit .env and fill in the required values:
   # KEYCLOAK_ADMIN=your_keycloak_admin_user_here
   # KEYCLOAK_ADMIN_PASSWORD=your_keycloak_admin_password_here
   # KC_HTTP_RELATIVE_PATH=your_keycloak_path_here
   ```

7. **Create Postgres Data Folder**
   ```bash
   mkdir data/postgres
   ```

8. **Start the Application**
   ```bash
   docker-compose up -d
   ```

## Production Setup

For production deployment, use the corresponding `_prod` files:

1. **Configure Docker Compose for Production**
   ```bash
   cp docker-compose.yml_prod docker-compose.yml
   ```

2. **Configure Nginx for Production**
   ```bash
   cp nginx/nginx.conf_prod nginx/nginx.conf
   ```

3. **Configure Frontend for Production**
   ```bash
   cp frontend/esa-chat-ui/vite.config_prod.js frontend/esa-chat-ui/vite.config.js
   ```

4. **Configure Frontend Environment**
   ```bash
   cp frontend/esa-chat-ui/.env-example frontend/esa-chat-ui/.env
   # Edit frontend/esa-chat-ui/.env and fill in the required values:
   # VITE_BACKEND_BASE_URL=your_backend_url_here
   # VITE_WMS_BASE_URL=your_wms_url_here
   ```

5. **Configure Backend Environment**
   ```bash
   cp backend/.env-example backend/.env
   # Edit backend/.env and fill in the required values:
   # API_KEY=your_api_key_here
   # AGENT_ID=your_agent_id_here
   # REDIS_HOST=your_redis_host_here
   ```

6. **Configure Global Environment**
   ```bash
   cp .env-example .env
   # Edit .env and fill in the required values:
   # KEYCLOAK_ADMIN=your_keycloak_admin_user_here
   # KEYCLOAK_ADMIN_PASSWORD=your_keycloak_admin_password_here
   # KC_HTTP_RELATIVE_PATH=your_keycloak_path_here
   ```

7. **Create Postgres Data Folder**
   ```bash
   mkdir data/postgres
   ```

8. **Start the Application**
   ```bash
   docker-compose up -d
   ```

## Project Structure
```
project-root/
├── docker-compose.yml          # Active configuration
├── docker-compose.yml_local    # Local template
├── docker-compose.yml_prod     # Production template
├── .env                        # Active composer environment variables
├── .env-example                # Template for composer environment variables
├── backend/
│   ├── .env                    # Active backend environment variables
│   └── .env-example            # Template for backend environment variables
├── nginx/
│   ├── nginx.conf             # Active nginx config
│   ├── nginx.conf_local       # Local nginx template
│   └── nginx.conf_prod        # Production nginx template
└── frontend/
    └── esa-chat-ui/
        ├── .env                  # Active frontend environment variables
        ├── .env-example          # Template for frontend environment variables
        ├── vite.config.js        # Active vite config
        ├── vite.config_local.js  # Local vite template
        └── vite.config_prod.js   # Production vite template
```

## Notes

- Make sure to add `docker-compose.yml`, `nginx/nginx.conf`, `frontend/esa-chat-ui/vite.config.js`, `frontend/esa-chat-ui/.env`, `backend/.env`, and `.env` to your `.gitignore` file to avoid committing environment-specific configurations
- Always verify your configuration files after copying from templates

## Authors
Developed by Fotini Patrona for the ESA AGENTS project
