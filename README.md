# Video to MP3 Converter Python Microservices

A distributed microservice application that converts video files to MP3 format using Python Flask, Docker, Kubernetes, RabbitMQ, MongoDB, and MySQL.

## Architecture Overview

```
Client → Gateway → MongoDB (video storage)
                ↓
            RabbitMQ (video queue)
                ↓
            Converter Service → MongoDB (mp3 storage)
                ↓
            RabbitMQ (mp3 queue)
                ↓
            Notification Service → Email to Client
```

## Prerequisites

- Docker Desktop
- Kubernetes CLI (`kubectl`)
- Minikube
- Python 3.10+
- MySQL
- MongoDB
- K9s (optional)

## Installation & Setup

### 1. Install Required Tools

```bash
# macOS
brew install kubectl minikube k9s
brew tap mongodb/brew
brew install mongodb-community
brew install mysql

# Start services
brew services start mongodb-community
brew services start mysql
minikube start
minikube addons enable ingress
```

### 2. Configure Local DNS

Edit `/etc/hosts`:
```bash
sudo vim /etc/hosts

# Add these lines:
127.0.0.1    mp3converter.com
127.0.0.1    rabbitmq-manager.com
```
**Note:** If `mp3converter.com` does not work for you, try using another domain name of your choice.

### 3. Database Setup

#### MySQL Setup for Auth Service

1. **Edit `auth/init.sql`** with your credentials:
```sql
CREATE USER 'authuser'@'localhost' IDENTIFIED BY 'your_password_here';
CREATE DATABASE auth;
GRANT ALL PRIVILEGES ON auth.* TO 'authuser'@'localhost';
USE auth;

CREATE TABLE user (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL
);

-- Insert your test user (update email and password as needed)
INSERT INTO user (email, password) VALUES ('your_email@example.com', 'your_password');
```

2. **Initialize the database**:
```bash
cd python/src/auth
mysql -u root < init.sql
```

#### MongoDB Setup

MongoDB databases will be created automatically when first used. Verify MongoDB is running:
```bash
mongo --eval "db.runCommand({ping: 1})"
```

### 4. Create Environment Configuration Files

Since secrets are not committed, create these files:

#### Auth Service (`auth/manifests/secret.yaml`)
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: auth-secret
stringData:
  MYSQL_PASSWORD: "your_mysql_password"
  JWT_SECRET: "your_jwt_secret_key"
type: Opaque
```

#### Gateway Service (`gateway/manifests/secret.yaml`)
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: gateway-secret
stringData:
  PLACEHOLDER: "nothing"
type: Opaque
```

#### Converter Service (`converter/manifests/secret.yaml`)
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: converter-secret
stringData:
  PLACEHOLDER: "none"
type: Opaque
```

#### Notification Service (`notification/manifests/secret.yaml`)
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: notification-secret
stringData:
  GMAIL_ADDRESS: "your_gmail@gmail.com"
  GMAIL_APP_PASSWORD: "your_gmail_app_password"
type: Opaque
```

**Note**: For Gmail, enable 2FA and create an App Password instead of using your regular password. You can find more information [here](https://support.google.com/accounts/answer/185833?hl=en).

#### RabbitMQ Service (`rabbit/manifests/secret.yaml`)
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: rabbitmq-secret
stringData:
  PLACEHOLDER: "nothing"
type: Opaque
```

## Building and Deployment

### 1. Build Docker Images

Replace `<your-dockerhub-username>` with your Docker Hub username:

```bash
# For each service (auth, gateway, converter, notification)
cd python/src/<service>
docker build -t <your-dockerhub-username>/<service>:latest .
docker push <your-dockerhub-username>/<service>:latest
```

### 2. Update Kubernetes Manifests

In each service's `manifests/<service>-deploy.yaml`, update the image name. Edit the following lines in the `<service>-deploy.yaml` file:
```yaml
spec:
  containers:
  - name: <service>
    image: <your-dockerhub-username>/<service>:latest
```

### 3. Deploy Services

```bash
# Deploy in this order
kubectl apply -f python/src/auth/manifests/
kubectl apply -f python/src/rabbit/manifests/
kubectl apply -f python/src/gateway/manifests/
kubectl apply -f python/src/converter/manifests/
kubectl apply -f python/src/notification/manifests/
```

### 4. Configure RabbitMQ

1. Start tunnel (keep running): `sudo minikube tunnel`
2. Access RabbitMQ: http://rabbitmq-manager.com (guest/guest)
3. Create two durable queues: `video` and `mp3`

## Usage

### 1. Login
```bash
curl -X POST http://mp3converter.com/login \
  -u <email>:<password>
```
Save/copy the returned JWT token.

### 2. Upload Video
```bash
curl -X POST http://mp3converter.com/upload \
  -F "file=@your_video.mp4" \
  -H "Authorization: Bearer <JWT_TOKEN>"
```

### 3. Check Email
You'll receive an email with the MP3 file ID.

### 4. Download MP3
```bash
curl -X GET "http://mp3converter.com/download?fid=<FILE_ID>" \
  -H "Authorization: Bearer <JWT_TOKEN>" \
  -o output.mp3
```

## Project Structure

```
.
├── python/
│   └── src/
│       ├── auth/
│       │   ├── server.py
│       │   ├── init.sql
│       │   ├── requirements.txt
│       │   ├── Dockerfile
│       │   └── manifests/
│       ├── gateway/
│       │   ├── server.py
│       │   ├── auth/
│       │   ├── auth_svc/
│       │   ├── storage/
│       │   └── manifests/
│       ├── converter/
│       │   ├── consumer.py
│       │   ├── convert/
│       │   └── manifests/
│       ├── notification/
│       │   ├── consumer.py
│       │   ├── send/
│       │   └── manifests/
│       └── rabbit/
│           └── manifests/
```

## Troubleshooting

### MongoDB Connection Issues
```bash
# Check if MongoDB is running
brew services list | grep mongodb
# Start if needed
brew services start mongodb-community
```

### RabbitMQ Connection Issues
After RabbitMQ restarts, restart Gateway:
```bash
kubectl rollout restart deployment gateway
```

### View Logs
```bash
kubectl logs -f <pod-name>
# Or use k9s for interactive monitoring
k9s
```

### Common Fixes
- Ensure `minikube tunnel` is running
- Check all pods are running: `kubectl get pods`
- Verify queues exist in RabbitMQ
- Check service logs for specific errors

## Security Notes

- Never commit secrets to version control
- Use strong passwords for database users
- In production, use proper secret management (e.g., Kubernetes Secrets, HashiCorp Vault)
- Enable SSL/TLS for all services in production
- Use network policies to restrict inter-service communication

## Cleanup

```bash
# Delete all deployments
kubectl delete -f python/src/auth/manifests/
kubectl delete -f python/src/gateway/manifests/
kubectl delete -f python/src/converter/manifests/
kubectl delete -f python/src/notification/manifests/
kubectl delete -f python/src/rabbit/manifests/

# Stop minikube
minikube stop

# Stop local services
brew services stop mongodb-community
brew services stop mysql
```

## Credits
This project is based on the [microservice architecture tutorial](https://www.youtube.com/watch?v=hmkF77F9TLw) by freeCodeCamp and [@kantancoding](@kantancoding).