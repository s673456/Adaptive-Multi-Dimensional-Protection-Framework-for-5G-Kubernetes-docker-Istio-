#!/usr/bin/env python3
"""
Multi-Agent Online Decision Service (NumPy-only, no torch)
Linear policy + REINFORCE with manual gradient.
"""

import os
import time
import logging
import numpy as np
from kubernetes import client, config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ========== Configuration ==========
SERVICES = ['amf', 'smf', 'upf']
NAMESPACE = "default"
DECISION_INTERVAL = 10
UPDATE_INTERVAL = 5
MAX_REPLICAS = 10
MIN_REPLICAS = 2
CLEANING_CYCLE_MIN = 10
CLEANING_CYCLE_MAX = 30
CLEANING_CYCLE_STEP = 3
ACTION_DIM = 7
LOCAL_STATE_DIM = 4
GLOBAL_STATE_DIM = 2
TOTAL_STATE_DIM = LOCAL_STATE_DIM + GLOBAL_STATE_DIM
LR = 0.001
GAMMA = 0.99

# Policy weights
weights = {}
episode_states = {}
episode_actions = {}
episode_rewards = {}
step_counter = 0

# Kubernetes clients
apps_v1 = None
core_v1 = None
networking_v1 = None

# ========== Policy ==========
def softmax(x):
    e = np.exp(x - np.max(x))
    return e / np.sum(e)

def init_policies():
    for svc in SERVICES:
        weights[svc] = np.random.randn(TOTAL_STATE_DIM, ACTION_DIM) * 0.01
        episode_states[svc] = []
        episode_actions[svc] = []
        episode_rewards[svc] = []
    logger.info(f"Initialized {len(SERVICES)} linear policies (input={TOTAL_STATE_DIM}, output={ACTION_DIM})")

def get_action(service, state):
    logits = state @ weights[service]
    probs = softmax(logits)
    action = np.random.choice(ACTION_DIM, p=probs)
    return action, probs[action]

def update_policy(service):
    states = episode_states[service]
    actions = episode_actions[service]
    rewards = episode_rewards[service]
    if len(rewards) == 0:
        return
    # Discounted returns
    returns = []
    R = 0
    for r in reversed(rewards):
        R = r + GAMMA * R
        returns.insert(0, R)
    returns = np.array(returns)
    returns = (returns - returns.mean()) / (returns.std() + 1e-8)
    # Gradient for linear softmax
    grad = np.zeros_like(weights[service])
    for t, (s, a, G) in enumerate(zip(states, actions, returns)):
        logits = s @ weights[service]
        probs = softmax(logits)
        grad += np.outer(s, (np.eye(ACTION_DIM)[a] - probs)) * G
    weights[service] += LR * grad
    # Clear buffers
    episode_states[service] = []
    episode_actions[service] = []
    episode_rewards[service] = []
    logger.info(f"Updated policy for {service}")

# ========== Kubernetes State Collection ==========
def get_deployment_replicas(name):
    try:
        dep = apps_v1.read_namespaced_deployment(name, NAMESPACE)
        return dep.spec.replicas
    except:
        return 2

def get_cleaning_cycle(service):
    cm_name = f"{service}-config"
    try:
        cm = core_v1.read_namespaced_config_map(cm_name, NAMESPACE)
        return int(cm.data.get("cleaning_cycle", "20"))
    except:
        return 20

def get_firewall_status(service):
    vs_name = f"{service}-firewall"
    try:
        networking_v1.read_namespaced_virtual_service(vs_name, NAMESPACE)
        return True
    except:
        return False

def get_request_rate(service):
    # Replace with real monitoring
    return np.random.uniform(0.2, 2.0)

def get_response_time(service):
    # Replace with real monitoring
    return np.random.uniform(0.1, 1.0)

def get_resource_usage():
    total = 0
    for svc in SERVICES:
        total += get_deployment_replicas(svc) * 10
    return total

def collect_local_state(service):
    replicas = get_deployment_replicas(service)
    cycle = get_cleaning_cycle(service)
    firewall = get_firewall_status(service)
    rate = get_request_rate(service)
    replica_norm = min(replicas / MAX_REPLICAS, 1.0)
    cycle_norm = min((cycle - CLEANING_CYCLE_MIN) / (CLEANING_CYCLE_MAX - CLEANING_CYCLE_MIN), 1.0)
    fw_flag = 1.0 if firewall else 0.0
    rate_norm = min(rate / 5.0, 1.0)
    return np.array([replica_norm, cycle_norm, fw_flag, rate_norm], dtype=np.float32)

def collect_global_state():
    resp_times = [get_response_time(svc) for svc in SERVICES]
    avg_rt = np.mean(resp_times)
    rt_norm = min(avg_rt / 2.0, 1.0)
    resource = get_resource_usage()
    res_norm = min(resource / 100.0, 1.0)
    return np.array([rt_norm, res_norm], dtype=np.float32)

def get_state_for_agent(service):
    local = collect_local_state(service)
    global_state = collect_global_state()
    return np.concatenate([local, global_state])

# ========== Action Execution ==========
def update_replicas(service, new_replicas):
    try:
        dep = apps_v1.read_namespaced_deployment(service, NAMESPACE)
        dep.spec.replicas = new_replicas
        apps_v1.patch_namespaced_deployment(service, NAMESPACE, dep)
        logger.info(f"Scaled {service} to {new_replicas}")
    except Exception as e:
        logger.error(f"Scale failed: {e}")

def update_cleaning_cycle(service, new_cycle):
    cm_name = f"{service}-config"
    try:
        cm = core_v1.read_namespaced_config_map(cm_name, NAMESPACE)
        if cm.data is None:
            cm.data = {}
        cm.data["cleaning_cycle"] = str(new_cycle)
        core_v1.patch_namespaced_config_map(cm_name, NAMESPACE, cm)
    except:
        body = client.V1ConfigMap(metadata=client.V1ObjectMeta(name=cm_name),
                                  data={"cleaning_cycle": str(new_cycle)})
        core_v1.create_namespaced_config_map(NAMESPACE, body)
    logger.info(f"Cleaning cycle for {service} -> {new_cycle}s")

def update_firewall(service, enabled):
    vs_name = f"{service}-firewall"
    if enabled:
        vs_body = {
            "apiVersion": "networking.istio.io/v1beta1",
            "kind": "VirtualService",
            "metadata": {"name": vs_name, "namespace": NAMESPACE},
            "spec": {
                "hosts": [service],
                "http": [
                    {"match": [{"headers": {"X-Attack-Target": {"exact": service}}}],
                     "fault": {"abort": {"percentage": {"value": 100}, "httpStatus": 403}}},
                    {"route": [{"destination": {"host": service, "port": {"number": 80}}}]}
                ]
            }
        }
        try:
            networking_v1.patch_namespaced_virtual_service(vs_name, NAMESPACE, vs_body)
        except:
            networking_v1.create_namespaced_virtual_service(NAMESPACE, vs_body)
    else:
        try:
            networking_v1.delete_namespaced_virtual_service(vs_name, NAMESPACE)
        except:
            pass
    logger.info(f"Firewall for {service} {'ENABLED' if enabled else 'DISABLED'}")

def execute_action(service, action):
    if action == 0:
        cur = get_deployment_replicas(service)
        if cur < MAX_REPLICAS:
            update_replicas(service, cur+1)
    elif action == 1:
        cur = get_deployment_replicas(service)
        if cur > MIN_REPLICAS:
            update_replicas(service, cur-1)
    elif action == 2:
        cur = get_cleaning_cycle(service)
        new_cycle = min(cur + CLEANING_CYCLE_STEP, CLEANING_CYCLE_MAX)
        update_cleaning_cycle(service, new_cycle)
    elif action == 3:
        cur = get_cleaning_cycle(service)
        new_cycle = max(cur - CLEANING_CYCLE_STEP, CLEANING_CYCLE_MIN)
        update_cleaning_cycle(service, new_cycle)
    elif action == 4:
        update_firewall(service, True)
    elif action == 5:
        update_firewall(service, False)
    # action 6: keep

def apply_actions(actions_dict):
    for svc, act in actions_dict.items():
        execute_action(svc, act)

# ========== Reward ==========
def compute_reward():
    resp_times = [get_response_time(svc) for svc in SERVICES]
    avg_rt = np.mean(resp_times)
    resource = get_resource_usage()
    return -avg_rt - 0.01 * resource

# ========== Main Loop ==========
def decision_loop():
    global step_counter
    while True:
        time.sleep(DECISION_INTERVAL)
        actions = {}
        for svc in SERVICES:
            state = get_state_for_agent(svc)
            action, prob = get_action(svc, state)
            actions[svc] = action
            episode_states[svc].append(state)
            episode_actions[svc].append(action)
        apply_actions(actions)
        reward = compute_reward()
        for svc in SERVICES:
            episode_rewards[svc].append(reward)
        step_counter += 1
        logger.info(f"Step {step_counter}: actions={actions}, reward={reward:.3f}")
        if step_counter % UPDATE_INTERVAL == 0:
            for svc in SERVICES:
                update_policy(svc)

# ========== Kubernetes Client Init ==========
def init_k8s_clients():
    global apps_v1, core_v1, networking_v1
    try:
        config.load_incluster_config()
    except:
        config.load_kube_config()
    apps_v1 = client.AppsV1Api()
    core_v1 = client.CoreV1Api()
    try:
        networking_v1 = client.NetworkingV1beta1Api()
    except:
        networking_v1 = client.CustomObjectsApi()
    logger.info("Kubernetes clients initialized")

if __name__ == "__main__":
    init_k8s_clients()
    init_policies()
    decision_loop()