#!/usr/bin/env bash
# In-cluster sanity request: proves gateway -> EPP -> vLLM before a real run.
NS=dhl-wva-209
GW=http://infra-llmdbench-inference-gateway-istio.${NS}.svc.cluster.local:80
kubectl run "sanity-$$" -n "$NS" --rm -i --restart=Never \
  --image=curlimages/curl:latest --timeout=180s -- \
  curl -s -m 60 -w '\nHTTP=%{http_code}\n' \
  -X POST "$GW/v1/completions" \
  -H 'Content-Type: application/json' \
  -d '{"model":"unsloth/Meta-Llama-3.1-8B-Instruct","prompt":"Say hello in five words.","max_tokens":16}'
