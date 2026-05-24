#!/bin/bash

# Create index.html
cat <<EOF > index.html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>OrdinoxAI Landing Page</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <header>
    <h1>OrdinoxAI Landing Page</h1>
  </header>
  <main>
    <section class="factory">
      <div class="conveyor-belt"></div>
      <div class="robot-arm"></div>
      <div class="ai-agent"></div>
    </section>
    <section class="contact">
      <h2>Join Our Waiting List</h2>
      <form>
        <input type="email" placeholder="Enter your email" required>
        <button type="submit">Submit</button>
      </form>
    </section>
  </main>
  <script src="script.js"></script>
</body>
</html>
EOF

# Create style.css
cat <<EOF > style.css
body {
  font-family: Arial, sans-serif;
  margin: 0;
  padding: 0;
  background-color: #f5f5f5;
}

header {
  background-color: #333;
  color: #fff;
  padding: 20px;
  text-align: center;
}

main {
  display: flex;
  justify-content: space-around;
  align-items: center;
  min-height: calc(100vh - 100px);
}

.factory {
  position: relative;
  width: 400px;
  height: 300px;
  background-color: #fff;
  border: 2px solid #333;
  border-radius: 10px;
  overflow: hidden;
}

.conveyor-belt {
  position: absolute;
  bottom: 20px;
  left: 0;
  width: 100%;
  height: 20px;
  background-color: #ccc;
  animation: conveyor-belt-animation 5s linear infinite;
}

.robot-arm {
  position: absolute;
  top: 50px;
  left: 50px;
  width: 100px;
  height: 150px;
  background-color: #999;
  transform-origin: bottom center;
  animation: robot-arm-animation 5s ease-in-out infinite;
}

.ai-agent {
  position: absolute;
  bottom: 60px;
  left: -50px;
  width: 50px;
  height: 50px;
  background-color: #4caf50;
  border-radius: 50%;
  animation: ai-agent-animation 5s linear infinite;
}

.contact {
  text-align: center;
}

.contact h2 {
  margin-bottom: 20px;
}

.contact input[type="email"] {
  padding: 10px;
  width: 300px;
  font-size: 16px;
  border-radius: 5px;
  border: 1px solid #ccc;
}

.contact button {
  padding: 10px 20px;
  font-size: 16px;
  background-color: #4caf50;
  color: #fff;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  margin-left: 10px;
}

@keyframes conveyor-belt-animation {
  0% {
    transform: translateX(0);
  }
  100% {
    transform: translateX(-100%);
  }
}

@keyframes robot-arm-animation {
  0%,
  100% {
    transform: rotate(0deg);
  }
  50% {
    transform: rotate(-45deg);
  }
}

@keyframes ai-agent-animation {
  0% {
    transform: translateX(0);
  }
  100% {
    transform: translateX(calc(400px + 100%));
  }
}
EOF

# Create script.js
cat <<EOF > script.js
// Add any necessary JavaScript code here
EOF

# Create ConfigMap
kubectl create configmap landing-page-files --from-file=index.html --from-file=style.css --from-file=script.js -n synthetic-enterprise

# Update landing-page-deployment.yaml
cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: landing-page
  namespace: synthetic-enterprise
spec:
  replicas: 1
  selector:
    matchLabels:
      app: landing-page
  template:
    metadata:
      labels:
        app: landing-page
    spec:
      containers:
      - name: landing-page
        image: nginx
        ports:
        - containerPort: 80
        volumeMounts:
        - name: nginx-config
          mountPath: /etc/nginx/conf.d
        - name: landing-page-content
          mountPath: /usr/share/nginx/html
      volumes:
      - name: nginx-config
        configMap:
          name: landing-page-config
      - name: landing-page-content
        configMap:
          name: landing-page-files
EOF

# Verify deployment
kubectl get deployment landing-page -n synthetic-enterprise
kubectl get pods -l app=landing-page -n synthetic-enterprise
