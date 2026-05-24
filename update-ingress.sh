#!/bin/bash

   # Update aia-api-ingress
   cat <<EOF | kubectl apply -f -
   apiVersion: networking.k8s.io/v1
   kind: Ingress
   metadata:
     name: aia-api-ingress
     namespace: synthetic-enterprise
     annotations:
       nginx.ingress.kubernetes.io/rewrite-target: /$1
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

   # Verify Ingress resource
   echo "Verifying Ingress resource..."
   kubectl describe ingress aia-api-ingress -n synthetic-enterprise

   # Test access to https://api.ordinoxai.com
   echo "Testing access to https://api.ordinoxai.com..."
   curl -v https://api.ordinoxai.com
