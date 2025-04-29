# -*- coding: utf-8 -*-
# pylint: disable=broad-exception-caught
import json
from kubernetes import client


async def k8s_top_nodes(sort_by=None):
    """
    Display resource usage (CPU/memory) of nodes.

    :param sort_by: Field to sort by (cpu or memory).
    :return: The resource usage of nodes.
    """
    try:
        # Get the resource usage using the Kubernetes Python SDK
        try:
            # Get the API client
            core_v1 = client.CoreV1Api()

            # Get the nodes
            nodes = core_v1.list_node()

            # Get the metrics API
            metrics_api = client.CustomObjectsApi()

            # Get the node metrics
            node_metrics = metrics_api.list_cluster_custom_object(
                "metrics.k8s.io", "v1beta1", "nodes"
            )

            # Format the node metrics
            formatted_nodes = []
            for node in nodes.items:
                node_name = node.metadata.name

                # Find the metrics for this node
                node_metric = next(
                    (
                        m
                        for m in node_metrics["items"]
                        if m["metadata"]["name"] == node_name
                    ),
                    None,
                )

                if node_metric:
                    # Extract CPU and memory usage
                    cpu_usage = node_metric["usage"]["cpu"]
                    memory_usage = node_metric["usage"]["memory"]

                    # Extract CPU and memory capacity
                    cpu_capacity = node.status.capacity["cpu"]
                    memory_capacity = node.status.capacity["memory"]

                    # Parse CPU usage value and convert to millicores for display
                    cpu_value_millicores = 0
                    if cpu_usage.endswith("n"):
                        # Nanocores to millicores
                        cpu_value_millicores = int(cpu_usage[:-1]) / 1000000
                    elif cpu_usage.endswith("u"):
                        # Microcores to millicores
                        cpu_value_millicores = int(cpu_usage[:-1]) / 1000
                    elif cpu_usage.endswith("m"):
                        # Already in millicores
                        cpu_value_millicores = int(cpu_usage[:-1])
                    else:
                        # Cores to millicores
                        cpu_value_millicores = float(cpu_usage) * 1000

                    # Parse CPU capacity (typically in cores)
                    cpu_capacity_value = float(cpu_capacity)

                    # Convert capacity from cores to millicores for percentage calculation
                    cpu_capacity_millicores = cpu_capacity_value * 1000

                    # Calculate CPU percentage (millicores / millicores)
                    cpu_percentage = (
                        cpu_value_millicores / cpu_capacity_millicores
                    ) * 100

                    # Parse memory usage value to bytes
                    memory_value_bytes = parse_memory_to_bytes(memory_usage)

                    # Parse memory capacity to bytes
                    memory_capacity_bytes = parse_memory_to_bytes(memory_capacity)

                    # Calculate memory percentage
                    memory_percentage = 0
                    if memory_capacity_bytes > 0:
                        memory_percentage = (
                            memory_value_bytes / memory_capacity_bytes
                        ) * 100

                    # Format memory for display in appropriate units
                    memory_display = format_bytes_to_human_readable(memory_value_bytes)

                    formatted_nodes.append(
                        {
                            "name": node_name,
                            "cpu": f"{int(cpu_value_millicores)}m ({cpu_percentage:.0f}%)",
                            "memory": f"{memory_display} ({memory_percentage:.0f}%)",
                        }
                    )

            # Sort the nodes if requested
            if sort_by:
                sort_by = sort_by.lower()
                if sort_by in ["cpu", "memory"]:
                    # Extract the percentage for sorting
                    def extract_percentage(value):
                        return float(value.split("(")[1].split("%")[0])

                    formatted_nodes.sort(
                        key=lambda x: extract_percentage(x.get(sort_by, "0 (0.0%)")),
                        reverse=True,
                    )

            return json.dumps(formatted_nodes, indent=2)

        except Exception as e:
            return f"Error: {str(e)}"
    except Exception as exc:
        return "Error:\n" + str(exc)


def format_bytes_to_human_readable(bytes_value):
    """
    Format bytes to human readable format (Ki, Mi, Gi)

    :param bytes_value: Bytes value to format
    :return: Formatted string
    """
    # Convert to MiB for better readability
    if bytes_value >= (1024 * 1024 * 1024):
        return f"{bytes_value / (1024 * 1024 * 1024):.0f}Gi"
    else:
        return f"{bytes_value / (1024 * 1024):.0f}Mi"


def parse_memory_to_bytes(memory_str):
    """
    Parse Kubernetes memory string to bytes.

    :param memory_str: Memory string (e.g., "100Mi", "2Gi", "1000Ki")
    :return: Memory value in bytes
    """
    if not memory_str:
        return 0

    # Remove trailing 'B' if present (e.g., "100MiB" -> "100Mi")
    if memory_str.endswith("B"):
        memory_str = memory_str[:-1]

    # Handle binary units
    if memory_str.endswith("Ki"):
        return float(memory_str[:-2]) * 1024
    elif memory_str.endswith("Mi"):
        return float(memory_str[:-2]) * 1024 * 1024
    elif memory_str.endswith("Gi"):
        return float(memory_str[:-2]) * 1024 * 1024 * 1024
    elif memory_str.endswith("Ti"):
        return float(memory_str[:-2]) * 1024 * 1024 * 1024 * 1024
    elif memory_str.endswith("Pi"):
        return float(memory_str[:-2]) * 1024 * 1024 * 1024 * 1024 * 1024
    elif memory_str.endswith("Ei"):
        return float(memory_str[:-2]) * 1024 * 1024 * 1024 * 1024 * 1024 * 1024

    # Handle decimal units
    elif memory_str.endswith("K") or memory_str.endswith("k"):
        return float(memory_str[:-1]) * 1000
    elif memory_str.endswith("M") or memory_str.endswith("m"):
        return float(memory_str[:-1]) * 1000 * 1000
    elif memory_str.endswith("G") or memory_str.endswith("g"):
        return float(memory_str[:-1]) * 1000 * 1000 * 1000
    elif memory_str.endswith("T") or memory_str.endswith("t"):
        return float(memory_str[:-1]) * 1000 * 1000 * 1000 * 1000
    elif memory_str.endswith("P") or memory_str.endswith("p"):
        return float(memory_str[:-1]) * 1000 * 1000 * 1000 * 1000 * 1000
    elif memory_str.endswith("E") or memory_str.endswith("e"):
        return float(memory_str[:-1]) * 1000 * 1000 * 1000 * 1000 * 1000 * 1000

    # No unit, assume bytes
    else:
        return float(memory_str)


async def k8s_top_pods(
    namespace=None, all_namespaces=False, sort_by=None, selector=None
):
    """
    Display resource usage (CPU/memory) of pods.

    :param namespace: The namespace to get pods from. If not specified, uses the default namespace.
    :param all_namespaces: Whether to get pods from all namespaces.
    :param sort_by: Field to sort by (cpu or memory).
    :param selector: Label selector to filter pods.
    :return: The resource usage of pods.
    """
    try:
        # Set default namespace if not provided and not all namespaces
        if not namespace and not all_namespaces:
            namespace = "default"

        # Get the API clients
        core_v1 = client.CoreV1Api()
        metrics_api = client.CustomObjectsApi()

        # Get the pods
        if all_namespaces:
            pods = core_v1.list_pod_for_all_namespaces(label_selector=selector)
            pod_metrics = metrics_api.list_cluster_custom_object(
                group="metrics.k8s.io", version="v1beta1", plural="pods"
            )
        else:
            pods = core_v1.list_namespaced_pod(namespace, label_selector=selector)
            pod_metrics = metrics_api.list_namespaced_custom_object(
                group="metrics.k8s.io",
                version="v1beta1",
                namespace=namespace,
                plural="pods",
            )

        # Format the pod metrics
        formatted_pods = []
        for pod in pods.items:
            pod_name = pod.metadata.name
            pod_namespace = pod.metadata.namespace

            # Find the metrics for this pod
            pod_metric = next(
                (
                    m
                    for m in pod_metrics["items"]
                    if m["metadata"]["name"] == pod_name
                    and m["metadata"]["namespace"] == pod_namespace
                ),
                None,
            )

            if not pod_metric:
                continue

            # Calculate total CPU and memory usage
            total_cpu_millicores = 0
            total_memory_bytes = 0

            for container in pod_metric["containers"]:
                # Extract CPU usage
                cpu_usage = container["usage"]["cpu"]

                # Parse CPU value based on unit
                if cpu_usage.endswith("n"):
                    # Nanocores to millicores
                    cpu_millicores = int(cpu_usage[:-1]) / 1000000
                elif cpu_usage.endswith("u"):
                    # Microcores to millicores
                    cpu_millicores = int(cpu_usage[:-1]) / 1000
                elif cpu_usage.endswith("m"):
                    # Already in millicores
                    cpu_millicores = int(cpu_usage[:-1])
                else:
                    # Cores to millicores
                    cpu_millicores = float(cpu_usage) * 1000

                total_cpu_millicores += cpu_millicores

                # Extract memory usage using the existing parse_memory_to_bytes function
                memory_usage = container["usage"]["memory"]
                memory_bytes = parse_memory_to_bytes(memory_usage)
                total_memory_bytes += memory_bytes

            # Format the memory for display in appropriate units
            memory_display = format_bytes_to_human_readable(total_memory_bytes)

            formatted_pods.append(
                {
                    "name": pod_name,
                    "namespace": pod_namespace,
                    "cpu": f"{int(total_cpu_millicores)}m",
                    "memory": memory_display,
                }
            )

        # Sort the pods if requested
        if sort_by:
            sort_by = sort_by.lower()
            if sort_by == "cpu":
                formatted_pods.sort(
                    key=lambda x: float(x["cpu"].rstrip("m")), reverse=True
                )
            elif sort_by == "memory":
                # For memory, we need to convert to bytes first for accurate sorting
                def memory_to_bytes(memory_str):
                    if memory_str.endswith("Mi"):
                        return float(memory_str[:-2]) * 1024 * 1024
                    elif memory_str.endswith("Gi"):
                        return float(memory_str[:-2]) * 1024 * 1024 * 1024
                    return 0

                formatted_pods.sort(
                    key=lambda x: memory_to_bytes(x["memory"]), reverse=True
                )

        return json.dumps(formatted_pods, indent=2)

    except (client.ApiException, ValueError) as e:
        return f"Error: {str(e)}"
    except Exception as exc:
        return f"Unexpected error: {str(exc)}"
