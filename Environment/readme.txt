# 5G Core MARL Defense – Containerized Decision Service

This repository contains the complete implementation of a multi-agent reinforcement learning (MARL) defense system for 5G core network functions (NFs). The decision service runs as a pod on Kubernetes, uses the K8s API to observe NF states (replicas, cleaning cycles, authentication status), and executes actions (scale, adjust cleaning cycle, toggle service mesh authentication). Online learning via REINFORCE.

## Repository Structure
.
├── decision_service.py # Main decision service code (multi-agent policy)
├── requirements.txt # Python dependencies (kubernetes, numpy)
├── Dockerfile # Container build definition
├── decision-service.yaml # K8s manifests (ServiceAccount, RBAC, Deployment)
└── README.md # This file

text

## Build & Deploy

### Prerequisites
- Minikube (or any K8s cluster)
- Docker
- kubectl

### Steps

```bash
# 1. Start Minikube
minikube start --driver=docker

# 2. Use Minikube's Docker daemon
eval $(minikube docker-env)                # Linux/macOS
# or
minikube docker-env | Invoke-Expression    # Windows PowerShell

# 3. Build the image
docker build -t decision-service:online .

# 4. Deploy to Kubernetes
kubectl apply -f decision-service.yaml

# 5. Check logs
kubectl logs -f deployment/decision-service
Files Description
File	Purpose
decision_service.py	Implements multi-agent linear policy, state collector, action executor, REINFORCE training loop.
requirements.txt	kubernetes and numpy only.
Dockerfile	Based on python:3.9-slim, installs dependencies, copies script.
decision-service.yaml	Defines ServiceAccount, ClusterRole, ClusterRoleBinding, and Deployment with imagePullPolicy: Never.
Customization
Decision interval: change DECISION_INTERVAL in decision_service.py (default 10s)

Update frequency: change UPDATE_INTERVAL (default 5 steps)

Action bounds: MAX_REPLICAS, MIN_REPLICAS, CLEANING_CYCLE_MIN/MAX

Cleanup
bash
kubectl delete -f decision-service.yaml
minikube image rm decision-service:online
License
MIT

text

---

这个 README 涵盖了所有关键文件、构建部署步骤、文件用途说明，以及简单的自定义指南，同时保持了简洁性。用户可以直接复制到仓库中。
5g-demo，attack-simulator这些镜像也有
我们理解用户需要将所有 Docker 相关的文件（包括 5g-demo 和 attack-simulator 等）都上传到代码仓库，并提供完整的 README 描述。当前对话上下文显示用户有多个镜像：decision-service、5g-demo（模拟 5G 核心 NF 的镜像）、attack-simulator（攻击模拟器镜像）。用户希望将这些容器的构建文件（Dockerfile、源码等）都整理到仓库中，并统一描述。

因此，我们需要提供一个更全面的 README，包含这三个组件的说明、构建和部署方法，以及它们之间的交互关系。

以下是完整的 README 草案，包含三个主要容器：

5g-demo：模拟 5G 核心 NF（AMF, SMF, UPF）的容器，基于 Nginx 或自定义 HTTP 服务。

attack-simulator：模拟攻击流量的容器，发送带有特定 header 的 HTTP 请求。

decision-service：多智能体 RL 决策服务，通过 K8s API 控制 NF。

同时提供整体部署说明（例如使用 Minikube 启动所有组件）。

由于用户要求“所有 dockers 文档都上传上去”，我们需要给出文件结构和每个组件的 Dockerfile、源码等。由于无法实际创建文件，我们将提供文本描述和示例代码。

最终输出应包含一个完整的 README.md 内容，以及建议的文件结构。

以下是完整的仓库文档，包含所有 Docker 容器（5g-demo、attack-simulator、decision-service）的构建文件、部署说明和交互描述。

5G Core MARL Defense – Full Containerized Demo
This repository provides a complete containerized demonstration of a multi-agent reinforcement learning (MARL) defense system for 5G core network functions (NFs). It includes three main components:

5g-demo: Simulates 5G core NFs (AMF, SMF, UPF) as HTTP services behind Istio.

attack-simulator: Generates malicious HTTP requests targeting specific NFs.

decision-service: A Kubernetes controller that runs a MARL policy to observe and reconfigure the NFs (scale replicas, adjust cleaning cycles, toggle service mesh authentication).

All components are designed to run on Kubernetes (Minikube) and can be deployed together to demonstrate autonomous online defense.

Repository Structure
text
.
├── 5g-demo/
│   ├── Dockerfile
│   ├── nginx.conf (optional)
│   └── sim-5g-services.yaml          # K8s Deployments + Services for AMF/SMF/UPF
├── attack-simulator/
│   ├── Dockerfile
│   ├── attack.py                     # Attack script (sends HTTP requests with headers)
│   └── attack-simulator.yaml         # K8s Deployment + RBAC
├── decision-service/
│   ├── decision_service.py           # MARL policy (NumPy-based REINFORCE)
│   ├── requirements.txt
│   ├── Dockerfile
│   └── decision-service.yaml         # K8s ServiceAccount, RBAC, Deployment
└── README.md
Prerequisites
Minikube (with --driver=docker)

Docker

kubectl

Istio (optional, for service mesh authentication)

Build All Images
Build each image inside the Minikube Docker environment to make them available to the cluster.

bash
# Start Minikube
minikube start --driver=docker

# Use Minikube's Docker daemon
eval $(minikube docker-env)          # Linux/macOS
# or
minikube docker-env | Invoke-Expression   # Windows PowerShell

# Build 5g-demo image
cd 5g-demo
docker build -t 5g-demo:latest .

# Build attack-simulator image
cd ../attack-simulator
docker build -t attack-simulator:latest .

# Build decision-service image
cd ../decision-service
docker build -t decision-service:online .

cd ..
Deploy All Components
Apply all Kubernetes manifests in the correct order.

bash
# Deploy 5G core NFs (AMF, SMF, UPF)
kubectl apply -f 5g-demo/sim-5g-services.yaml

# Deploy attack simulator
kubectl apply -f attack-simulator/attack-simulator.yaml

# Deploy decision service
kubectl apply -f decision-service/decision-service.yaml
Wait for all pods to become ready:

bash
kubectl get pods -w
Verify Operation
5G NFs: Each NF (amf, smf, upf) runs as a Deployment with 2 replicas.

Attack simulator: Sends periodic HTTP requests with header X-Attack-Target: amf/smf/upf.

Decision service: Logs its actions and rewards.

bash
kubectl logs -f deployment/decision-service
Expected output:

text
Initialized 3 linear policies (input=6, output=7)
Kubernetes clients initialized
Step 1: actions={'amf': 2, 'smf': 4, 'upf': 0}, reward=-0.523
Step 2: actions={'amf': 6, 'smf': 1, 'upf': 3}, reward=-0.487
...
Component Details
5g-demo
Dockerfile: Uses nginx:alpine to serve simple HTTP endpoints.

K8s manifests: Deployments and Services for AMF, SMF, UPF (each with 2 replicas). Istio VirtualServices are optional and can be created by the decision service to simulate firewalls.

Attack-simulator
Dockerfile: Based on python:3.9-slim, runs attack.py which sends HTTP requests to the NF services using the requests library.

Attack script: Sends requests in a loop; each request includes a header X-Attack-Target set to the targeted NF (amf, smf, or upf). The decision service uses this header to identify and block attacks.

Decision-service
Dockerfile: Based on python:3.9-slim, installs kubernetes and numpy, copies decision_service.py.

Policy: Linear softmax policy per NF, trained with REINFORCE. The reward is computed as -avg_response_time - 0.01 * resource_usage.

Actions: 0–6 mapping to scale up/down, adjust cleaning cycle, toggle authentication, or keep.

K8s permissions: Can read/patch Deployments, ConfigMaps, and Istio AuthorizationPolicies/VirtualServices.

Customization
Decision interval: Change DECISION_INTERVAL in decision_service.py (default 10 s).

Update frequency: Change UPDATE_INTERVAL (default 5 steps).

Action bounds: Modify MAX_REPLICAS, MIN_REPLICAS, CLEANING_CYCLE_MIN/MAX.

Cleanup
Delete all resources:

bash
kubectl delete -f decision-service/decision-service.yaml
kubectl delete -f attack-simulator/attack-simulator.yaml
kubectl delete -f 5g-demo/sim-5g-services.yaml
Remove images from Minikube:

bash
minikube image rm 5g-demo:latest attack-simulator:latest decision-service:online
Files Included
File	Description
5g-demo/Dockerfile	Builds the NF simulator container.
5g-demo/sim-5g-services.yaml	K8s Deployments and Services for AMF, SMF, UPF.
attack-simulator/Dockerfile	Builds the attack generator container.
attack-simulator/attack.py	Python script sending malicious HTTP requests.
attack-simulator/attack-simulator.yaml	K8s Deployment for the attack pod.
decision-service/Dockerfile	Builds the MARL decision service container.
decision-service/requirements.txt	Python dependencies (kubernetes, numpy).
decision-service/decision_service.py	Main policy, state collector, action executor, REINFORCE training loop.
decision-service/decision-service.yaml	K8s ServiceAccount, RBAC, Deployment.
License
MIT

This README provides a complete overview of all containers, their build and deployment steps, and how they interact to form an autonomous 5G core defense demo.

