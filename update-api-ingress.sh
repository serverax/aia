#!/bin/bash

# Update aia-api-ingress
cat <<EOF | kubectl apply -f -
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: aia-api-ingress
  namespace: synthetic-enterprise
spec:
	  ingressClassName: nginx
  tls:
  - hosts:
    - api.ordinoxai.com
    secretName: aia-api-tls
  rules:
  - host: api.ordinoxai.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: aia-api-service
            port:
              number: 80
EOF

# Update aia-api-service
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Service
metadata:
  name: aia-api-service
  namespace: synthetic-enterprise
spec:
  type: ExternalName
  externalName: api.ordinoxai.com
EOF

# Verify Ingress resource
echo "Verifying Ingress resource..."
kubectl describe ingress aia-api-ingress -n synthetic-enterprise

# Verify ExternalName service
echo "Verifying ExternalName service..."
kubectl describe service aia-api-service -n synthetic-enterprise
# Update aia-api-ingress
   cat <<EOF | kubectl apply -f -
   apiVersion: networking.k8s.io/v1
   kind: Ingress
   metadata:
     name: aia-api-ingress
     namespace: synthetic-enterprise
     annotations:
       nginx.ingress.kubernetes.io/rewrite-target: /$2
   spec:
     ingressClassName: nginx
     tls:
     - hosts:
       - api.ordinoxai.com
       secretName: aia-api-tls
     rules:
     - host: api.ordinoxai.com
       http:
         paths:
         - path: /()(.*)
           pathType: Prefix
           backend:
             service:
               name: aia-api-service
               port:
                 number: 80
   EOF
