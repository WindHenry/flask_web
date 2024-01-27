#!/bin/bash
POD_NAME=${POD_NAME:-default}
NODE_NAME=${NODE_NAME:-default}
POD_NAME_SOURCE=${POD_NAME_SOURCE:-default}
POD_NAME_DESTINATION=${POD_NAME_DESTINATION:-default}
MIN=${MIN:-default}
MAX=${MAX:-default}

EVENT=${EVENT:-default}

if [ "$EVENT" == "LIST-POD" ]; then 
  kubectl get pods -n kube-system -o custom-columns="POD_NAME:.metadata.name,IP:.status.podIP,NODE_NAME:.spec.nodeName,STATUS:.status.phase"
fi

if [ "$EVENT" == "LIST-POD-KUBE-OVN" ]; then 
  kubectl ko nbctl list Logical_Switch_Port
fi

if [ "$EVENT" == "LIST-NODE" ]; then 
  kubectl get nodes -o custom-columns=NAME:.metadata.name --no-headers
fi

if [ "$EVENT" == "CREATE-POD" ]; then
  cat <<EOF > test_pinger.yaml 
  apiVersion: v1
  kind: Pod
  metadata:
    name: $POD_NAME
    namespace: kube-system
    labels:
      app: $POD_NAME
  spec:
    containers:
    - name: ubuntu
      image: ubuntu:20.04
      command: ["/bin/sleep", "infinity"]
      ports:
      - containerPort: 80
EOF
  kubectl apply -f test_pinger.yaml > /dev/null 2>&1
  # Kiểm tra trạng thái mỗi giây trong 30 giây
  for ((i=0; i<30; i++)); do
    STATUS=$(kubectl get pod $POD_NAME -o jsonpath='{.status.phase}' -n kube-system)
    if [ "$STATUS" == "Running" ]; then
      echo "true"
      exit 0
    else
      sleep 1
    fi
  done

  # Nếu không chuyển sang Running trong 30 giây, báo lỗi
  echo "false"
fi

if [ "$EVENT" == "CREATE-QOS" ]; then
  status=$(kubectl ko nbctl queue-add "$POD_NAME_DESTINATION.kube-system" to-lport 200 'inport=="'"$POD_NAME_SOURCE.kube-system"'"' minr="$MIN" rate="$MAX")

  if [ "$status" == "" ]; then 
    listPodSource=$(kubectl ko nbctl queue-list "$POD_NAME_DESTINATION.kube-system" | grep -o 'inport=="[^"]*"' | cut -d'"' -f2)

    declare -a inport_array

    while IFS= read -r line; do
      inport_array+=("$line")
    done <<< "$listPodSource"

    found=false
    for inport in "${inport_array[@]}"; do
      if [ "$inport" == "$POD_NAME_SOURCE.kube-system" ]; then
        found=true
        break
      fi
    done

    if $found; then
      echo "true"
    else
      echo "false"
    fi
  else
    echo $status
  fi
fi

if [ "$EVENT" == "LIST-QUEUES" ]; then 
  kubectl ko nbctl queue-list "$POD_NAME_DESTINATION.kube-system"
fi

