# -*- coding: utf-8 -*-
# pylint: disable=broad-exception-caught
import base64
import json
import os
from kubernetes import client, config, dynamic
from .get import _get_group_versions, DateTimeEncoder


def gen_kubeconfig():
    """Generate a kubeconfig for the current Pod."""
    token = (
        open("/run/secrets/kubernetes.io/serviceaccount/token", "r", encoding="utf-8")
        .read()
        .strip()
    )  # Strip newline characters
    cert = (
        open("/run/secrets/kubernetes.io/serviceaccount/ca.crt", "r", encoding="utf-8")
        .read()
        .strip()
    )  # Strip newline characters
    cert = base64.b64encode(cert.encode()).decode()
    host = os.environ.get("KUBERNETES_SERVICE_HOST")
    port = os.environ.get("KUBERNETES_SERVICE_PORT")

    return f"""apiVersion: v1
clusters:
- cluster:
    certificate-authority-data: {cert}
    server: https://{host}:{port}
  name: kube
contexts:
- context:
    cluster: kube
    user: kube
  name: kube
current-context: kube
kind: Config
users:
- name: kube
  user:
    token: {token}
"""


def setup_kubeconfig():
    """Set up kubeconfig if running inside a Pod."""
    if os.getenv("KUBECONFIG") is not None and os.getenv("KUBECONFIG") != "":
        return

    if not os.getenv("KUBERNETES_SERVICE_HOST"):
        # Not running inside a Pod, so no need to set up kubeconfig
        return

    home = os.path.expanduser("~")  # Use expanduser to get user's home directory
    kubeconfig_path = os.path.join(home, ".kube")
    kubeconfig_file = os.path.join(kubeconfig_path, "config")

    # If kubeconfig already exists, no need to recreate it
    if os.path.exists(kubeconfig_file):
        return

    os.makedirs(kubeconfig_path, exist_ok=True)
    kubeconfig = gen_kubeconfig()
    with open(kubeconfig_file, "w", encoding="utf-8") as f:
        f.write(kubeconfig)


def setup_client():
    """Get a Kubernetes client."""

    setup_kubeconfig()
    try:
        config.load_kube_config()
    except Exception:
        config.load_incluster_config()

    configuration = client.Configuration.get_default_copy()
    configuration.debug = True
    client.Configuration.set_default(configuration)
    return client


async def k8s_cordon(node_name):
    """
    Mark a node as unschedulable.

    :param node_name: The name of the node to cordon.
    :return: The result of the cordon operation.
    """
    try:
        # Cordon using the Kubernetes Python SDK
        try:
            # Get the API client
            core_v1 = client.CoreV1Api()

            # Create a patch to set unschedulable to true
            patch = {"spec": {"unschedulable": True}}

            # Update the node
            core_v1.patch_node(
                node_name,
                patch,
            )

            return f"Node {node_name} cordoned successfully"

        except Exception as e:
            return f"Error: {str(e)}"
    except Exception as exc:
        return "Error:\n" + str(exc)


async def k8s_uncordon(node_name):
    """
    Mark a node as schedulable.

    :param node_name: The name of the node to uncordon.
    :return: The result of the uncordon operation.
    """
    try:
        # Uncordon using the Kubernetes Python SDK
        try:
            # Get the API client
            core_v1 = client.CoreV1Api()

            # Create a patch to set unschedulable to false
            patch = {"spec": {"unschedulable": False}}

            # Update the node
            core_v1.patch_node(
                node_name,
                patch,
            )

            return f"Node {node_name} uncordoned successfully"

        except Exception as e:
            return f"Error: {str(e)}"
    except Exception as exc:
        return "Error:\n" + str(exc)


async def k8s_annotate(
    resource_type,
    name=None,
    annotations=None,
    namespace=None,
    selector=None,
    all_namespaces=False,
    overwrite=False,
    resource_version=None,
    dry_run=False,
):
    """
    Update the annotations on a resource.

    :param resource_type: The type of resource to annotate (e.g., pods, deployments).
    :param name: The name of the resource to annotate. If not specified, annotates resources matching the selector.
    :param annotations: The annotations to add or update as a dictionary or comma-separated string (e.g., "key1=value1,key2=value2").
    :param namespace: The namespace of the resource. If not specified, uses the default namespace.
    :param selector: Label selector to filter resources (e.g., "app=nginx").
    :param all_namespaces: Whether to annotate resources in all namespaces.
    :param overwrite: If true, overwrite existing annotations.
    :param resource_version: Only update if the resource version matches.
    :param dry_run: If true, only print the object that would be sent, without sending it.
    :return: The result of the annotate operation.
    """
    try:
        # Set default namespace if not provided and not all namespaces
        if not namespace and not all_namespaces:
            namespace = "default"

        # Convert annotations to dictionary if it's a string
        if isinstance(annotations, str):
            annotations_dict = {}
            for annotation in annotations.split(","):
                if "=" in annotation:
                    key, value = annotation.split("=", 1)
                    annotations_dict[key] = value
                elif "-" in annotation:
                    key = annotation.strip("-")
                    annotations_dict[key] = None  # Mark for removal
            annotations = annotations_dict

        # Annotate using the Kubernetes Python SDK
        try:
            # Get the API client
            api_client = client.ApiClient()

            # Get the resources to annotate
            resources = []

            if name:
                # Get a specific resource
                if resource_type.lower() == "pod":
                    core_v1 = client.CoreV1Api()
                    resources.append(core_v1.read_namespaced_pod(name, namespace))
                elif resource_type.lower() == "service":
                    core_v1 = client.CoreV1Api()
                    resources.append(core_v1.read_namespaced_service(name, namespace))
                elif resource_type.lower() == "deployment":
                    apps_v1 = client.AppsV1Api()
                    resources.append(
                        apps_v1.read_namespaced_deployment(name, namespace)
                    )
                elif resource_type.lower() == "statefulset":
                    apps_v1 = client.AppsV1Api()
                    resources.append(
                        apps_v1.read_namespaced_stateful_set(name, namespace)
                    )
                elif resource_type.lower() == "daemonset":
                    apps_v1 = client.AppsV1Api()
                    resources.append(
                        apps_v1.read_namespaced_daemon_set(name, namespace)
                    )
                elif resource_type.lower() == "configmap":
                    core_v1 = client.CoreV1Api()
                    resources.append(
                        core_v1.read_namespaced_config_map(name, namespace)
                    )
                elif resource_type.lower() == "secret":
                    core_v1 = client.CoreV1Api()
                    resources.append(core_v1.read_namespaced_secret(name, namespace))
                elif resource_type.lower() == "persistentvolumeclaim":
                    core_v1 = client.CoreV1Api()
                    resources.append(
                        core_v1.read_namespaced_persistent_volume_claim(name, namespace)
                    )
                elif resource_type.lower() == "persistentvolume":
                    core_v1 = client.CoreV1Api()
                    resources.append(core_v1.read_persistent_volume(name))
                elif resource_type.lower() == "node":
                    core_v1 = client.CoreV1Api()
                    resources.append(core_v1.read_node(name))
                else:
                    # Use the dynamic client for other resource types
                    dyn = dynamic.DynamicClient(api_client)

                    # Find the resource
                    resource_found = False
                    resource_client = None

                    # Try to find the resource in different API groups
                    for group, version in _get_group_versions(api_client):
                        path = (
                            f"/api/{version}"
                            if group == ""
                            else f"/apis/{group}/{version}"
                        )
                        try:
                            reslist = api_client.call_api(
                                path,
                                "GET",
                                response_type="object",
                                _return_http_data_only=True,
                            )
                        except client.exceptions.ApiException:
                            continue  # Skip if no permission or API not available

                        for r in reslist["resources"]:
                            if (
                                r.get("name") == f"{resource_type}s"
                                or r.get("name") == resource_type
                            ):
                                gv = version if group == "" else f"{group}/{version}"
                                resource_client = dyn.resources.get(
                                    api_version=gv, kind=r["kind"]
                                )
                                resource_found = True
                                break

                        if resource_found:
                            break

                    if not resource_found or not resource_client:
                        return f"Error: resource type '{resource_type}' not found"

                    # Get the resource
                    if resource_client.namespaced:
                        resources.append(
                            resource_client.get(name=name, namespace=namespace)
                        )
                    else:
                        resources.append(resource_client.get(name=name))
            else:
                # Get resources matching the selector
                if resource_type.lower() == "pod":
                    core_v1 = client.CoreV1Api()
                    if all_namespaces:
                        pods = core_v1.list_pod_for_all_namespaces(
                            label_selector=selector
                        )
                    else:
                        pods = core_v1.list_namespaced_pod(
                            namespace, label_selector=selector
                        )
                    resources.extend(pods.items)
                elif resource_type.lower() == "service":
                    core_v1 = client.CoreV1Api()
                    if all_namespaces:
                        services = core_v1.list_service_for_all_namespaces(
                            label_selector=selector
                        )
                    else:
                        services = core_v1.list_namespaced_service(
                            namespace, label_selector=selector
                        )
                    resources.extend(services.items)
                elif resource_type.lower() == "deployment":
                    apps_v1 = client.AppsV1Api()
                    if all_namespaces:
                        deployments = apps_v1.list_deployment_for_all_namespaces(
                            label_selector=selector
                        )
                    else:
                        deployments = apps_v1.list_namespaced_deployment(
                            namespace, label_selector=selector
                        )
                    resources.extend(deployments.items)
                elif resource_type.lower() == "statefulset":
                    apps_v1 = client.AppsV1Api()
                    if all_namespaces:
                        statefulsets = apps_v1.list_stateful_set_for_all_namespaces(
                            label_selector=selector
                        )
                    else:
                        statefulsets = apps_v1.list_namespaced_stateful_set(
                            namespace, label_selector=selector
                        )
                    resources.extend(statefulsets.items)
                elif resource_type.lower() == "daemonset":
                    apps_v1 = client.AppsV1Api()
                    if all_namespaces:
                        daemonsets = apps_v1.list_daemon_set_for_all_namespaces(
                            label_selector=selector
                        )
                    else:
                        daemonsets = apps_v1.list_namespaced_daemon_set(
                            namespace, label_selector=selector
                        )
                    resources.extend(daemonsets.items)
                else:
                    # Use the dynamic client for other resource types
                    dyn = dynamic.DynamicClient(api_client)

                    # Find the resource
                    resource_found = False
                    resource_client = None

                    # Try to find the resource in different API groups
                    for group, version in _get_group_versions(api_client):
                        path = (
                            f"/api/{version}"
                            if group == ""
                            else f"/apis/{group}/{version}"
                        )
                        try:
                            reslist = api_client.call_api(
                                path,
                                "GET",
                                response_type="object",
                                _return_http_data_only=True,
                            )
                        except client.exceptions.ApiException:
                            continue  # Skip if no permission or API not available

                        for r in reslist["resources"]:
                            if (
                                r.get("name") == f"{resource_type}s"
                                or r.get("name") == resource_type
                            ):
                                gv = version if group == "" else f"{group}/{version}"
                                resource_client = dyn.resources.get(
                                    api_version=gv, kind=r["kind"]
                                )
                                resource_found = True
                                break

                        if resource_found:
                            break

                    if not resource_found or not resource_client:
                        return f"Error: resource type '{resource_type}' not found"

                    # Get the resources
                    if resource_client.namespaced:
                        if all_namespaces:
                            resource_list = resource_client.list(
                                label_selector=selector
                            )
                        else:
                            resource_list = resource_client.list(
                                namespace=namespace, label_selector=selector
                            )
                    else:
                        resource_list = resource_client.list(label_selector=selector)

                    resources.extend(resource_list.items)

            # Update the annotations on each resource
            updated_resources = []

            for resource in resources:
                # Check resource version if specified
                if (
                    resource_version
                    and resource.metadata.resource_version != resource_version
                ):
                    continue

                # Update the annotations
                if not resource.metadata.annotations:
                    resource.metadata.annotations = {}

                for key, value in annotations.items():
                    if value is None:
                        # Remove the annotation
                        if key in resource.metadata.annotations:
                            del resource.metadata.annotations[key]
                    else:
                        # Add or update the annotation
                        if key in resource.metadata.annotations and not overwrite:
                            continue
                        resource.metadata.annotations[key] = value

                # Update the resource
                if resource.kind.lower() == "pod":
                    core_v1 = client.CoreV1Api()
                    result = core_v1.patch_namespaced_pod(
                        resource.metadata.name,
                        resource.metadata.namespace,
                        {"metadata": {"annotations": resource.metadata.annotations}},
                        dry_run="All" if dry_run else None,
                    )
                elif resource.kind.lower() == "service":
                    core_v1 = client.CoreV1Api()
                    result = core_v1.patch_namespaced_service(
                        resource.metadata.name,
                        resource.metadata.namespace,
                        {"metadata": {"annotations": resource.metadata.annotations}},
                        dry_run="All" if dry_run else None,
                    )
                elif resource.kind.lower() == "deployment":
                    apps_v1 = client.AppsV1Api()
                    result = apps_v1.patch_namespaced_deployment(
                        resource.metadata.name,
                        resource.metadata.namespace,
                        {"metadata": {"annotations": resource.metadata.annotations}},
                        dry_run="All" if dry_run else None,
                    )
                elif resource.kind.lower() == "statefulset":
                    apps_v1 = client.AppsV1Api()
                    result = apps_v1.patch_namespaced_stateful_set(
                        resource.metadata.name,
                        resource.metadata.namespace,
                        {"metadata": {"annotations": resource.metadata.annotations}},
                        dry_run="All" if dry_run else None,
                    )
                elif resource.kind.lower() == "daemonset":
                    apps_v1 = client.AppsV1Api()
                    result = apps_v1.patch_namespaced_daemon_set(
                        resource.metadata.name,
                        resource.metadata.namespace,
                        {"metadata": {"annotations": resource.metadata.annotations}},
                        dry_run="All" if dry_run else None,
                    )
                elif resource.kind.lower() == "node":
                    core_v1 = client.CoreV1Api()
                    result = core_v1.patch_node(
                        resource.metadata.name,
                        {"metadata": {"annotations": resource.metadata.annotations}},
                        dry_run="All" if dry_run else None,
                    )
                else:
                    # Use the dynamic client for other resource types
                    dyn = dynamic.DynamicClient(api_client)

                    # Find the resource client
                    api_version = resource.api_version
                    kind = resource.kind

                    # Get the resource client
                    resource_client = dyn.resources.get(
                        api_version=api_version, kind=kind
                    )

                    # Update the resource
                    if (
                        hasattr(resource.metadata, "namespace")
                        and resource.metadata.namespace
                    ):
                        result = resource_client.patch(
                            name=resource.metadata.name,
                            namespace=resource.metadata.namespace,
                            body={
                                "metadata": {
                                    "annotations": resource.metadata.annotations
                                }
                            },
                            dry_run="All" if dry_run else None,
                        )
                    else:
                        result = resource_client.patch(
                            name=resource.metadata.name,
                            body={
                                "metadata": {
                                    "annotations": resource.metadata.annotations
                                }
                            },
                            dry_run="All" if dry_run else None,
                        )

                updated_resources.append(
                    {
                        "kind": result.kind,
                        "apiVersion": result.api_version,
                        "metadata": {
                            "name": result.metadata.name,
                            "namespace": (
                                result.metadata.namespace
                                if hasattr(result.metadata, "namespace")
                                else None
                            ),
                            "annotations": result.metadata.annotations,
                        },
                    }
                )

            return updated_resources

        except Exception as e:
            return f"Error: {str(e)}"
    except Exception as exc:
        return "Error:\n" + str(exc)


async def k8s_label(
    resource_type,
    name=None,
    labels=None,
    namespace=None,
    selector=None,
    all_namespaces=False,
    overwrite=False,
    resource_version=None,
    dry_run=False,
):
    """
    Update the labels on a resource.

    :param resource_type: The type of resource to label (e.g., pods, deployments).
    :param name: The name of the resource to label. If not specified, labels resources matching the selector.
    :param labels: The labels to add or update as a dictionary or comma-separated string (e.g., "key1=value1,key2=value2").
    :param namespace: The namespace of the resource. If not specified, uses the default namespace.
    :param selector: Label selector to filter resources (e.g., "app=nginx").
    :param all_namespaces: Whether to label resources in all namespaces.
    :param overwrite: If true, overwrite existing labels.
    :param resource_version: Only update if the resource version matches.
    :param dry_run: If true, only print the object that would be sent, without sending it.
    :return: The result of the label operation.
    """
    try:
        # Set default namespace if not provided and not all namespaces
        if not namespace and not all_namespaces:
            namespace = "default"

        # Convert labels to dictionary if it's a string
        if isinstance(labels, str):
            labels_dict = {}
            for label in labels.split(","):
                if "=" in label:
                    key, value = label.split("=", 1)
                    labels_dict[key] = value
                elif "-" in label:
                    key = label.strip("-")
                    labels_dict[key] = None  # Mark for removal
            labels = labels_dict

        # Label using the Kubernetes Python SDK
        try:
            # Get the API client
            api_client = client.ApiClient()

            # Get the resources to label
            resources = []

            if name:
                # Get a specific resource
                if resource_type.lower() == "pod":
                    core_v1 = client.CoreV1Api()
                    resources.append(core_v1.read_namespaced_pod(name, namespace))
                elif resource_type.lower() == "service":
                    core_v1 = client.CoreV1Api()
                    resources.append(core_v1.read_namespaced_service(name, namespace))
                elif resource_type.lower() == "deployment":
                    apps_v1 = client.AppsV1Api()
                    resources.append(
                        apps_v1.read_namespaced_deployment(name, namespace)
                    )
                elif resource_type.lower() == "statefulset":
                    apps_v1 = client.AppsV1Api()
                    resources.append(
                        apps_v1.read_namespaced_stateful_set(name, namespace)
                    )
                elif resource_type.lower() == "daemonset":
                    apps_v1 = client.AppsV1Api()
                    resources.append(
                        apps_v1.read_namespaced_daemon_set(name, namespace)
                    )
                elif resource_type.lower() == "configmap":
                    core_v1 = client.CoreV1Api()
                    resources.append(
                        core_v1.read_namespaced_config_map(name, namespace)
                    )
                elif resource_type.lower() == "secret":
                    core_v1 = client.CoreV1Api()
                    resources.append(core_v1.read_namespaced_secret(name, namespace))
                elif resource_type.lower() == "persistentvolumeclaim":
                    core_v1 = client.CoreV1Api()
                    resources.append(
                        core_v1.read_namespaced_persistent_volume_claim(name, namespace)
                    )
                elif resource_type.lower() == "persistentvolume":
                    core_v1 = client.CoreV1Api()
                    resources.append(core_v1.read_persistent_volume(name))
                elif resource_type.lower() == "node":
                    core_v1 = client.CoreV1Api()
                    resources.append(core_v1.read_node(name))
                else:
                    # Use the dynamic client for other resource types
                    dyn = dynamic.DynamicClient(api_client)

                    # Find the resource
                    resource_found = False
                    resource_client = None

                    # Try to find the resource in different API groups
                    for group, version in _get_group_versions(api_client):
                        path = (
                            f"/api/{version}"
                            if group == ""
                            else f"/apis/{group}/{version}"
                        )
                        try:
                            reslist = api_client.call_api(
                                path,
                                "GET",
                                response_type="object",
                                _return_http_data_only=True,
                            )
                        except client.exceptions.ApiException:
                            continue  # Skip if no permission or API not available

                        for r in reslist["resources"]:
                            if (
                                r.get("name") == f"{resource_type}s"
                                or r.get("name") == resource_type
                            ):
                                gv = version if group == "" else f"{group}/{version}"
                                resource_client = dyn.resources.get(
                                    api_version=gv, kind=r["kind"]
                                )
                                resource_found = True
                                break

                        if resource_found:
                            break

                    if not resource_found or not resource_client:
                        return f"Error: resource type '{resource_type}' not found"

                    # Get the resource
                    if resource_client.namespaced:
                        resources.append(
                            resource_client.get(name=name, namespace=namespace)
                        )
                    else:
                        resources.append(resource_client.get(name=name))
            else:
                # Get resources matching the selector
                if resource_type.lower() == "pod":
                    core_v1 = client.CoreV1Api()
                    if all_namespaces:
                        pods = core_v1.list_pod_for_all_namespaces(
                            label_selector=selector
                        )
                    else:
                        pods = core_v1.list_namespaced_pod(
                            namespace, label_selector=selector
                        )
                    resources.extend(pods.items)
                elif resource_type.lower() == "service":
                    core_v1 = client.CoreV1Api()
                    if all_namespaces:
                        services = core_v1.list_service_for_all_namespaces(
                            label_selector=selector
                        )
                    else:
                        services = core_v1.list_namespaced_service(
                            namespace, label_selector=selector
                        )
                    resources.extend(services.items)
                elif resource_type.lower() == "deployment":
                    apps_v1 = client.AppsV1Api()
                    if all_namespaces:
                        deployments = apps_v1.list_deployment_for_all_namespaces(
                            label_selector=selector
                        )
                    else:
                        deployments = apps_v1.list_namespaced_deployment(
                            namespace, label_selector=selector
                        )
                    resources.extend(deployments.items)
                elif resource_type.lower() == "statefulset":
                    apps_v1 = client.AppsV1Api()
                    if all_namespaces:
                        statefulsets = apps_v1.list_stateful_set_for_all_namespaces(
                            label_selector=selector
                        )
                    else:
                        statefulsets = apps_v1.list_namespaced_stateful_set(
                            namespace, label_selector=selector
                        )
                    resources.extend(statefulsets.items)
                elif resource_type.lower() == "daemonset":
                    apps_v1 = client.AppsV1Api()
                    if all_namespaces:
                        daemonsets = apps_v1.list_daemon_set_for_all_namespaces(
                            label_selector=selector
                        )
                    else:
                        daemonsets = apps_v1.list_namespaced_daemon_set(
                            namespace, label_selector=selector
                        )
                    resources.extend(daemonsets.items)
                else:
                    # Use the dynamic client for other resource types
                    dyn = dynamic.DynamicClient(api_client)

                    # Find the resource
                    resource_found = False
                    resource_client = None

                    # Try to find the resource in different API groups
                    for group, version in _get_group_versions(api_client):
                        path = (
                            f"/api/{version}"
                            if group == ""
                            else f"/apis/{group}/{version}"
                        )
                        try:
                            reslist = api_client.call_api(
                                path,
                                "GET",
                                response_type="object",
                                _return_http_data_only=True,
                            )
                        except client.exceptions.ApiException:
                            continue  # Skip if no permission or API not available

                        for r in reslist["resources"]:
                            if (
                                r.get("name") == f"{resource_type}s"
                                or r.get("name") == resource_type
                            ):
                                gv = version if group == "" else f"{group}/{version}"
                                resource_client = dyn.resources.get(
                                    api_version=gv, kind=r["kind"]
                                )
                                resource_found = True
                                break

                        if resource_found:
                            break

                    if not resource_found or not resource_client:
                        return f"Error: resource type '{resource_type}' not found"

                    # Get the resources
                    if resource_client.namespaced:
                        if all_namespaces:
                            resource_list = resource_client.list(
                                label_selector=selector
                            )
                        else:
                            resource_list = resource_client.list(
                                namespace=namespace, label_selector=selector
                            )
                    else:
                        resource_list = resource_client.list(label_selector=selector)

                    resources.extend(resource_list.items)

            # Update the labels on each resource
            updated_resources = []

            for resource in resources:
                # Check resource version if specified
                if (
                    resource_version
                    and resource.metadata.resource_version != resource_version
                ):
                    continue

                # Update the labels
                if not resource.metadata.labels:
                    resource.metadata.labels = {}

                for key, value in labels.items():
                    if value is None:
                        # Remove the label
                        if key in resource.metadata.labels:
                            del resource.metadata.labels[key]
                    else:
                        # Add or update the label
                        if key in resource.metadata.labels and not overwrite:
                            continue
                        resource.metadata.labels[key] = value

                # Update the resource
                if resource.kind.lower() == "pod":
                    core_v1 = client.CoreV1Api()
                    result = core_v1.patch_namespaced_pod(
                        resource.metadata.name,
                        resource.metadata.namespace,
                        {"metadata": {"labels": resource.metadata.labels}},
                        dry_run="All" if dry_run else None,
                    )
                elif resource.kind.lower() == "service":
                    core_v1 = client.CoreV1Api()
                    result = core_v1.patch_namespaced_service(
                        resource.metadata.name,
                        resource.metadata.namespace,
                        {"metadata": {"labels": resource.metadata.labels}},
                        dry_run="All" if dry_run else None,
                    )
                elif resource.kind.lower() == "deployment":
                    apps_v1 = client.AppsV1Api()
                    result = apps_v1.patch_namespaced_deployment(
                        resource.metadata.name,
                        resource.metadata.namespace,
                        {"metadata": {"labels": resource.metadata.labels}},
                        dry_run="All" if dry_run else None,
                    )
                elif resource.kind.lower() == "statefulset":
                    apps_v1 = client.AppsV1Api()
                    result = apps_v1.patch_namespaced_stateful_set(
                        resource.metadata.name,
                        resource.metadata.namespace,
                        {"metadata": {"labels": resource.metadata.labels}},
                        dry_run="All" if dry_run else None,
                    )
                elif resource.kind.lower() == "daemonset":
                    apps_v1 = client.AppsV1Api()
                    result = apps_v1.patch_namespaced_daemon_set(
                        resource.metadata.name,
                        resource.metadata.namespace,
                        {"metadata": {"labels": resource.metadata.labels}},
                        dry_run="All" if dry_run else None,
                    )
                elif resource.kind.lower() == "node":
                    core_v1 = client.CoreV1Api()
                    result = core_v1.patch_node(
                        resource.metadata.name,
                        {"metadata": {"labels": resource.metadata.labels}},
                        dry_run="All" if dry_run else None,
                    )
                else:
                    # Use the dynamic client for other resource types
                    dyn = dynamic.DynamicClient(api_client)

                    # Find the resource client
                    api_version = resource.api_version
                    kind = resource.kind

                    # Get the resource client
                    resource_client = dyn.resources.get(
                        api_version=api_version, kind=kind
                    )

                    # Update the resource
                    if (
                        hasattr(resource.metadata, "namespace")
                        and resource.metadata.namespace
                    ):
                        result = resource_client.patch(
                            name=resource.metadata.name,
                            namespace=resource.metadata.namespace,
                            body={"metadata": {"labels": resource.metadata.labels}},
                            dry_run="All" if dry_run else None,
                        )
                    else:
                        result = resource_client.patch(
                            name=resource.metadata.name,
                            body={"metadata": {"labels": resource.metadata.labels}},
                            dry_run="All" if dry_run else None,
                        )

                updated_resources.append(
                    {
                        "kind": result.kind,
                        "apiVersion": result.api_version,
                        "metadata": {
                            "name": result.metadata.name,
                            "namespace": (
                                result.metadata.namespace
                                if hasattr(result.metadata, "namespace")
                                else None
                            ),
                            "labels": result.metadata.labels,
                        },
                    }
                )

            return updated_resources

        except Exception as e:
            return f"Error: {str(e)}"
    except Exception as exc:
        return "Error:\n" + str(exc)


async def k8s_patch(resource_type, name, patch_data, namespace=None):
    """
    Update fields of a resource using a patch.

    :param resource_type: The type of resource to patch (e.g., pods, deployments).
    :param name: The name of the resource to patch.
    :param patch_data: The patch data as a JSON string or dictionary.
    :param namespace: The namespace of the resource. If not specified, uses the default namespace.
    :return: The result of the patch operation.
    """
    try:
        # Set default namespace if not provided
        if not namespace:
            namespace = "default"

        # Convert patch_data to string if it's a dictionary
        if isinstance(patch_data, dict):
            patch_data = json.dumps(patch_data)

        # Patch using the Kubernetes Python SDK
        try:
            # Get the API client
            api_client = client.ApiClient()

            # Parse the patch data
            if isinstance(patch_data, str):
                patch_obj = json.loads(patch_data)
            else:
                patch_obj = patch_data

            # Patch the resource
            if resource_type.lower() == "pod":
                core_v1 = client.CoreV1Api()
                result = core_v1.patch_namespaced_pod(
                    name,
                    namespace,
                    patch_obj,
                )
            elif resource_type.lower() == "service":
                core_v1 = client.CoreV1Api()
                result = core_v1.patch_namespaced_service(
                    name,
                    namespace,
                    patch_obj,
                )
            elif resource_type.lower() == "deployment":
                apps_v1 = client.AppsV1Api()
                result = apps_v1.patch_namespaced_deployment(
                    name,
                    namespace,
                    patch_obj,
                )
            elif resource_type.lower() == "statefulset":
                apps_v1 = client.AppsV1Api()
                result = apps_v1.patch_namespaced_stateful_set(
                    name,
                    namespace,
                    patch_obj,
                )
            elif resource_type.lower() == "daemonset":
                apps_v1 = client.AppsV1Api()
                result = apps_v1.patch_namespaced_daemon_set(
                    name,
                    namespace,
                    patch_obj,
                )
            elif resource_type.lower() == "configmap":
                core_v1 = client.CoreV1Api()
                result = core_v1.patch_namespaced_config_map(
                    name,
                    namespace,
                    patch_obj,
                )
            elif resource_type.lower() == "secret":
                core_v1 = client.CoreV1Api()
                result = core_v1.patch_namespaced_secret(
                    name,
                    namespace,
                    patch_obj,
                )
            elif resource_type.lower() == "persistentvolumeclaim":
                core_v1 = client.CoreV1Api()
                result = core_v1.patch_namespaced_persistent_volume_claim(
                    name,
                    namespace,
                    patch_obj,
                )
            elif resource_type.lower() == "persistentvolume":
                core_v1 = client.CoreV1Api()
                result = core_v1.patch_persistent_volume(name, patch_obj)
            elif resource_type.lower() == "node":
                core_v1 = client.CoreV1Api()
                result = core_v1.patch_node(name, patch_obj)
            else:
                # Use the dynamic client for other resource types
                dyn = dynamic.DynamicClient(api_client)

                # Find the resource
                resource_found = False
                resource_client = None

                # Try to find the resource in different API groups
                for group, version in _get_group_versions(api_client):
                    path = (
                        f"/api/{version}" if group == "" else f"/apis/{group}/{version}"
                    )
                    try:
                        reslist = api_client.call_api(
                            path,
                            "GET",
                            response_type="object",
                            _return_http_data_only=True,
                        )
                    except client.exceptions.ApiException:
                        continue  # Skip if no permission or API not available

                    for r in reslist["resources"]:
                        if (
                            r.get("name") == f"{resource_type}s"
                            or r.get("name") == resource_type
                        ):
                            gv = version if group == "" else f"{group}/{version}"
                            resource_client = dyn.resources.get(
                                api_version=gv, kind=r["kind"]
                            )
                            resource_found = True
                            break

                    if resource_found:
                        break

                if not resource_found or not resource_client:
                    return f"Error: resource type '{resource_type}' not found"

                # Check if the resource is namespaced
                if resource_client.namespaced:
                    result = resource_client.patch(
                        name=name,
                        namespace=namespace,
                        body=patch_obj,
                    )
                else:
                    result = resource_client.patch(
                        name=name,
                        body=patch_obj,
                    )

            # Return the result
            return {
                "kind": result.kind,
                "apiVersion": result.api_version,
                "metadata": {
                    "name": result.metadata.name,
                    "namespace": (
                        result.metadata.namespace
                        if hasattr(result.metadata, "namespace")
                        else None
                    ),
                    "uid": result.metadata.uid,
                    "resourceVersion": result.metadata.resource_version,
                },
                "status": "patched",
            }

        except Exception as e:
            return f"Error: {str(e)}"
    except Exception as exc:
        return "Error:\n" + str(exc)


async def k8s_exec_command(
    pod_name,
    command,
    container=None,
    namespace=None,
    stdin=False,
    tty=False,
    timeout=None,
):
    """
    Execute a command in a container.

    :param pod_name: The name of the pod.
    :param command: The command to execute.
    :param container: The name of the container in the pod. If not specified, uses the first container.
    :param namespace: The namespace of the pod. If not specified, uses the default namespace.
    :param stdin: Whether to pass stdin to the container.
    :param tty: Whether to allocate a TTY.
    :param timeout: The timeout for the command execution in seconds.
    :return: The output of the command.
    """
    try:
        # Set default namespace if not provided
        if not namespace:
            namespace = "default"

        # Get the API client
        core_v1 = client.CoreV1Api()

        try:
            # Get the pod
            pod = core_v1.read_namespaced_pod(pod_name, namespace)

            # If container is not specified, use the first container
            if not container:
                if pod.spec.containers:
                    container = pod.spec.containers[0].name
                else:
                    return "Error: No containers found in pod"

            # Import the stream function
            from kubernetes.stream import stream

            # Prepare the command
            if isinstance(command, str):
                exec_command = ["/bin/sh", "-c", command]
            else:
                exec_command = command

            # Set timeout value
            timeout_value = int(timeout) if timeout else 1

            # Execute the command
            resp = stream(
                core_v1.connect_get_namespaced_pod_exec,
                pod_name,
                namespace,
                command=exec_command,
                container=container,
                stdin=stdin,
                stdout=True,
                stderr=True,
                tty=tty,
                _preload_content=False,
            )

            # Get the output
            output = ""
            error = ""

            # Read the output
            while resp.is_open():
                resp.update(timeout=timeout_value)
                if resp.peek_stdout():
                    output += resp.read_stdout()
                if resp.peek_stderr():
                    error += resp.read_stderr()

            # Close the connection
            resp.close()

            # Return the output
            if error:
                return f"{output}\nError: {error}"
            else:
                return output

        except client.exceptions.ApiException as e:
            return f"Error: {str(e)}"
    except Exception as exc:
        return "Error:\n" + str(exc)


async def k8s_taint(node_name, key, value=None, effect=None, overwrite=False):
    """
    Update the taints on one or more nodes.

    :param node_name: The name of the node to taint.
    :param key: The taint key to add/remove.
    :param value: The taint value.
    :param effect: The taint effect (NoSchedule, PreferNoSchedule, NoExecute).
    :param overwrite: If true, overwrite any existing taint with the same key.
    :return: The result of the taint operation.
    """
    try:
        # Taint using the Kubernetes Python SDK
        try:
            # Get the API client
            core_v1 = client.CoreV1Api()

            # Get the node
            node = core_v1.read_node(node_name)

            # Get the current taints
            current_taints = node.spec.taints or []

            # Check if the taint already exists
            taint_exists = False
            for i, taint in enumerate(current_taints):
                if taint.key == key:
                    taint_exists = True
                    if overwrite:
                        # Update the taint
                        current_taints[i].value = value
                        current_taints[i].effect = effect
                    break

            # Add the taint if it doesn't exist
            if not taint_exists:
                current_taints.append(
                    client.V1Taint(key=key, value=value, effect=effect)
                )

            # Create a patch to update the taints
            patch = {
                "spec": {
                    "taints": [
                        {"key": t.key, "value": t.value, "effect": t.effect}
                        for t in current_taints
                    ]
                }
            }

            # Update the node
            core_v1.patch_node(
                node_name,
                patch,
            )

            return f"Node {node_name} tainted successfully"

        except Exception as e:
            return f"Error: {str(e)}"
    except Exception as exc:
        return "Error:\n" + str(exc)


async def k8s_untaint(node_name, key, effect=None):
    """
    Remove the taints from one or more nodes.

    :param node_name: The name of the node to untaint.
    :param key: The taint key to remove.
    :param effect: The taint effect (NoSchedule, PreferNoSchedule, NoExecute).
    :return: The result of the untaint operation.
    """
    try:
        # Untaint using the Kubernetes Python SDK
        try:
            # Get the API client
            core_v1 = client.CoreV1Api()

            # Get the node
            node = core_v1.read_node(node_name)

            # Get the current taints
            current_taints = node.spec.taints or []

            # Filter out the taint to remove
            new_taints = []
            for taint in current_taints:
                if taint.key != key or (effect and taint.effect != effect):
                    new_taints.append(taint)

            # Create a patch to update the taints
            patch = {
                "spec": {
                    "taints": [
                        {"key": t.key, "value": t.value, "effect": t.effect}
                        for t in new_taints
                    ]
                }
            }

            # Update the node
            core_v1.patch_node(
                node_name,
                patch,
            )

            return f"Taint removed from node {node_name} successfully"

        except Exception as e:
            return f"Error: {str(e)}"
    except Exception as exc:
        return "Error:\n" + str(exc)


async def k8s_drain(
    node_name,
    ignore_daemonsets=False,
    delete_local_data=False,
    force=False,
    grace_period=None,
):
    """
    Drain a node in preparation for maintenance.

    :param node_name: The name of the node to drain.
    :param ignore_daemonsets: Whether to ignore DaemonSet-managed pods.
    :param delete_local_data: Whether to delete pods with local storage.
    :param force: Whether to continue even if there are pods not managed by a ReplicationController, ReplicaSet, Job, DaemonSet or StatefulSet.
    :param grace_period: Period of time in seconds given to each pod to terminate gracefully. If negative, the default value specified in the pod will be used.

    :return: The result of the drain operation.
    """
    try:
        # Implement drain using the Kubernetes Python SDK
        try:
            # First, cordon the node to prevent new pods from being scheduled
            core_v1 = client.CoreV1Api()

            # Cordon the node
            patch = {"spec": {"unschedulable": True}}
            core_v1.patch_node(
                node_name,
                patch,
            )

            # Get all pods on the node
            field_selector = f"spec.nodeName={node_name}"
            pods = core_v1.list_pod_for_all_namespaces(field_selector=field_selector)

            # Set up delete options
            delete_options = {}
            if grace_period is not None:
                delete_options["grace_period_seconds"] = int(grace_period)

            # Process each pod
            eviction_results = []
            for pod in pods.items:
                pod_namespace = pod.metadata.namespace
                pod_name = pod.metadata.name

                # Skip DaemonSet pods if ignore_daemonsets is True
                if ignore_daemonsets and pod.metadata.owner_references:
                    is_daemonset_pod = any(
                        owner.kind == "DaemonSet"
                        for owner in pod.metadata.owner_references
                    )
                    if is_daemonset_pod:
                        eviction_results.append(
                            {
                                "pod": f"{pod_namespace}/{pod_name}",
                                "status": "skipped",
                                "reason": "DaemonSet-managed pod",
                            }
                        )
                        continue

                # Check for local storage
                has_local_storage = False
                if pod.spec.volumes:
                    for volume in pod.spec.volumes:
                        if (hasattr(volume, "host_path") and volume.host_path) or (
                            hasattr(volume, "empty_dir") and volume.empty_dir
                        ):
                            has_local_storage = True
                            break

                if has_local_storage and not delete_local_data:
                    eviction_results.append(
                        {
                            "pod": f"{pod_namespace}/{pod_name}",
                            "status": "skipped",
                            "reason": "pod has local storage",
                        }
                    )
                    continue

                # Check if pod is managed by a controller
                is_managed = False
                if pod.metadata.owner_references:
                    is_managed = any(
                        owner.kind
                        in [
                            "ReplicationController",
                            "ReplicaSet",
                            "StatefulSet",
                            "DaemonSet",
                            "Job",
                        ]
                        for owner in pod.metadata.owner_references
                    )

                if not is_managed and not force:
                    eviction_results.append(
                        {
                            "pod": f"{pod_namespace}/{pod_name}",
                            "status": "skipped",
                            "reason": "pod not managed by a controller",
                        }
                    )
                    continue

                # Create an eviction for the pod
                try:
                    # Create eviction object
                    eviction = client.V1Eviction(
                        metadata=client.V1ObjectMeta(
                            name=pod_name, namespace=pod_namespace
                        ),
                        delete_options=client.V1DeleteOptions(
                            grace_period_seconds=delete_options.get(
                                "grace_period_seconds"
                            )
                        ),
                    )

                    # Evict the pod
                    core_v1.create_namespaced_pod_eviction(
                        name=pod_name, namespace=pod_namespace, body=eviction
                    )

                    eviction_results.append(
                        {"pod": f"{pod_namespace}/{pod_name}", "status": "evicted"}
                    )
                except client.exceptions.ApiException as e:
                    eviction_results.append(
                        {
                            "pod": f"{pod_namespace}/{pod_name}",
                            "status": "error",
                            "reason": str(e),
                        }
                    )

            # Format the results
            import json

            result_summary = {
                "node": node_name,
                "status": "cordoned",
                "evictions": eviction_results,
            }

            return json.dumps(result_summary, indent=2)

        except Exception as e:
            return f"Error: {str(e)}"
    except Exception as exc:
        return "Error:\n" + str(exc)


async def k8s_autoscale(
    resource_type, name, min_replicas, max_replicas, cpu_percent=None, namespace=None
):
    """
    Create a horizontal pod autoscaler for a deployment, replicaset, statefulset, or replication controller.

    :param resource_type: The type of resource to autoscale (deployment, replicaset, statefulset, replicationcontroller).
    :param name: The name of the resource to autoscale.
    :param min_replicas: The minimum number of replicas.
    :param max_replicas: The maximum number of replicas.
    :param cpu_percent: The target CPU utilization percentage. If not specified, uses the default (80%).
    :param namespace: The namespace of the resource. If not specified, uses the default namespace.
    :return: The result of the autoscaling operation.
    """
    try:
        # Set default namespace if not provided
        if not namespace:
            namespace = "default"

        # Set default CPU percent if not provided
        if not cpu_percent:
            cpu_percent = 80

        # Create the autoscaler using the Kubernetes Python SDK
        try:
            # Get the resource
            if resource_type.lower() in [
                "deployment",
                "replicaset",
                "statefulset",
                "replicationcontroller",
            ]:
                autoscaling_v1 = client.AutoscalingV1Api()

                # Create the HPA
                hpa = client.V1HorizontalPodAutoscaler(
                    api_version="autoscaling/v1",
                    kind="HorizontalPodAutoscaler",
                    metadata=client.V1ObjectMeta(name=name, namespace=namespace),
                    spec=client.V1HorizontalPodAutoscalerSpec(
                        scale_target_ref=client.V1CrossVersionObjectReference(
                            api_version=(
                                "apps/v1"
                                if resource_type.lower() != "replicationcontroller"
                                else "v1"
                            ),
                            kind=resource_type.capitalize(),
                            name=name,
                        ),
                        min_replicas=int(min_replicas),
                        max_replicas=int(max_replicas),
                        target_cpu_utilization_percentage=int(cpu_percent),
                    ),
                )

                # Create the HPA in the cluster
                autoscaling_v1.create_namespaced_horizontal_pod_autoscaler(
                    namespace=namespace, body=hpa
                )

                return f"Created autoscaler for {resource_type}/{name} with min={min_replicas}, max={max_replicas}, cpu-percent={cpu_percent}"

            else:
                return f"Error: resource type '{resource_type}' autoscaling not available through API"

        except Exception as e:
            return f"Error: {str(e)}"
    except Exception as exc:
        return "Error:\n" + str(exc)


async def k8s_scale(resource_type, name, replicas, namespace=None):
    """
    Scale a deployment, replicaset, statefulset, or replication controller.

    :param resource_type: The type of resource to scale (deployment, replicaset, statefulset, replicationcontroller).
    :param name: The name of the resource to scale.
    :param replicas: The number of replicas to scale to.
    :param namespace: The namespace of the resource. If not specified, uses the default namespace.
    :return: The result of the scaling operation.
    """
    try:
        # Set default namespace if not provided
        if not namespace:
            namespace = "default"

        # Scale using the Kubernetes Python SDK
        try:
            # Create a patch to set replicas
            patch = {"spec": {"replicas": int(replicas)}}

            # Get the resource
            if resource_type.lower() == "deployment":
                apps_v1 = client.AppsV1Api()

                # Update the Deployment
                apps_v1.patch_namespaced_deployment(
                    name,
                    namespace,
                    patch,
                )

                return (
                    f"Scaled {resource_type}/{name} to {replicas} replicas successfully"
                )

            elif resource_type.lower() == "replicaset":
                apps_v1 = client.AppsV1Api()

                # Update the ReplicaSet
                apps_v1.patch_namespaced_replica_set(
                    name,
                    namespace,
                    patch,
                )

                return (
                    f"Scaled {resource_type}/{name} to {replicas} replicas successfully"
                )

            elif resource_type.lower() == "statefulset":
                apps_v1 = client.AppsV1Api()

                # Update the StatefulSet
                apps_v1.patch_namespaced_stateful_set(
                    name,
                    namespace,
                    patch,
                )

                return (
                    f"Scaled {resource_type}/{name} to {replicas} replicas successfully"
                )

            elif resource_type.lower() == "replicationcontroller":
                core_v1 = client.CoreV1Api()

                # Update the ReplicationController
                core_v1.patch_namespaced_replication_controller(
                    name,
                    namespace,
                    patch,
                )

                return (
                    f"Scaled {resource_type}/{name} to {replicas} replicas successfully"
                )

            else:
                return f"Error: resource type '{resource_type}' scaling not available through API"

        except Exception as e:
            return f"Error: {str(e)}"
    except Exception as exc:
        return "Error:\n" + str(exc)


async def k8s_rollout_resume(resource_type, name, namespace=None):
    """
    Resume a rollout for a deployment or daemonset.

    :param resource_type: The type of resource (deployment, daemonset).
    :param name: The name of the resource.
    :param namespace: The namespace of the resource. If not specified, uses the default namespace.
    :return: The result of the resume operation.
    """
    try:
        # Set default namespace if not provided
        if not namespace:
            namespace = "default"

        # Resume using the Kubernetes Python SDK
        try:
            # Get the resource
            if resource_type.lower() == "deployment":
                apps_v1 = client.AppsV1Api()

                # Create a patch to set paused to false
                patch = {"spec": {"paused": False}}

                # Update the Deployment
                apps_v1.patch_namespaced_deployment(
                    name,
                    namespace,
                    patch,
                )

                return f"Resumed rollout of {resource_type}/{name} successfully"

            else:
                return f"Error: resource type '{resource_type}' resume not available through API"

        except Exception as e:
            return f"Error: {str(e)}"
    except Exception as exc:
        return "Error:\n" + str(exc)


async def k8s_delete(
    resource_type,
    name=None,
    namespace=None,
    label_selector=None,
    field_selector=None,
    all_namespaces=False,
    cascade=True,
    grace_period=None,
):
    """
    Delete Kubernetes resources by name, label selector, or field selector.

    :param resource_type: The type of resource to delete (e.g., pods, deployments).
    :param name: The name of the resource to delete. If not specified, deletes resources matching the selectors.
    :param namespace: The namespace of the resource. If not specified, uses the default namespace.
    :param label_selector: Label selector to filter resources (e.g., "app=nginx").
    :param field_selector: Field selector to filter resources (e.g., "metadata.name=nginx").
    :param all_namespaces: Whether to delete resources in all namespaces.
    :param cascade: Whether to cascade the deletion to dependent resources.
    :param grace_period: The grace period for the deletion in seconds.
    :return: The result of the deletion operation.
    """
    try:
        # Set default namespace if not provided and not all namespaces
        if not namespace and not all_namespaces:
            namespace = "default"

        # Get the API client
        api_client = client.ApiClient()
        dyn = dynamic.DynamicClient(api_client)

        # Find the resource to delete
        resource_found = False
        resource_client = None

        # Try to find the resource in different API groups
        for group, version in _get_group_versions(api_client):
            path = f"/api/{version}" if group == "" else f"/apis/{group}/{version}"
            try:
                reslist = api_client.call_api(
                    path, "GET", response_type="object", _return_http_data_only=True
                )
            except client.exceptions.ApiException:
                continue  # Skip if no permission or API not available

            for r in reslist["resources"]:
                if (
                    r.get("name") == f"{resource_type}s"
                    or r.get("name") == resource_type
                ):
                    gv = version if group == "" else f"{group}/{version}"
                    resource_client = dyn.resources.get(api_version=gv, kind=r["kind"])
                    resource_found = True
                    break

            if resource_found:
                break

        if not resource_found or not resource_client:
            return f"Error: resource type '{resource_type}' not found"

        # Prepare delete options
        delete_options = {}

        if not cascade:
            delete_options["propagation_policy"] = "Orphan"
        else:
            delete_options["propagation_policy"] = "Background"

        if grace_period is not None:
            delete_options["grace_period_seconds"] = int(grace_period)

        # Delete by name
        if name:
            if all_namespaces:
                # Need to find the namespace first
                all_resources = resource_client.get(
                    label_selector=label_selector, field_selector=field_selector
                )
                deleted = []

                for item in all_resources.items:
                    try:
                        resource_client.delete(
                            name=item.metadata.name,
                            namespace=item.metadata.namespace,
                            **delete_options,
                        )
                        deleted.append(
                            {
                                "name": item.metadata.name,
                                "namespace": item.metadata.namespace,
                                "status": "deleted",
                            }
                        )
                    except Exception as e:
                        deleted.append(
                            {
                                "name": item.metadata.name,
                                "namespace": item.metadata.namespace,
                                "status": "error",
                                "message": str(e),
                            }
                        )

                return json.dumps(deleted, indent=2)
            else:
                resource_client.delete(name=name, namespace=namespace, **delete_options)
                return json.dumps(
                    {"name": name, "namespace": namespace, "status": "deleted"},
                    indent=2,
                )
        else:
            # Delete by selectors
            if all_namespaces:
                all_resources = resource_client.get(
                    label_selector=label_selector, field_selector=field_selector
                )
                deleted = []

                for item in all_resources.items:
                    try:
                        resource_client.delete(
                            name=item.metadata.name,
                            namespace=item.metadata.namespace,
                            **delete_options,
                        )
                        deleted.append(
                            {
                                "name": item.metadata.name,
                                "namespace": item.metadata.namespace,
                                "status": "deleted",
                            }
                        )
                    except Exception as e:
                        deleted.append(
                            {
                                "name": item.metadata.name,
                                "namespace": item.metadata.namespace,
                                "status": "error",
                                "message": str(e),
                            }
                        )

                return json.dumps(deleted, indent=2)
            else:
                all_resources = resource_client.get(
                    namespace=namespace,
                    label_selector=label_selector,
                    field_selector=field_selector,
                )
                deleted = []

                for item in all_resources.items:
                    try:
                        resource_client.delete(
                            name=item.metadata.name,
                            namespace=namespace,
                            **delete_options,
                        )
                        deleted.append(
                            {"name": item.metadata.name, "status": "deleted"}
                        )
                    except Exception as e:
                        deleted.append(
                            {
                                "name": item.metadata.name,
                                "status": "error",
                                "message": str(e),
                            }
                        )

                return json.dumps(deleted, indent=2)

    except Exception as exc:
        return "Error:\n" + str(exc)


async def k8s_run(
    image,
    name,
    namespace=None,
    replicas=1,
    port=None,
    env=None,
    labels=None,
    limits=None,
    requests=None,
):
    """
    Run a specific image in the cluster by creating a deployment.

    :param image: The Docker image to run.
    :param name: The name for the deployment and pods.
    :param namespace: The namespace to run in. If not specified, uses the default namespace.
    :param replicas: The number of replicas to run. Default is 1.
    :param port: The port the container exposes, if any.
    :param env: Environment variables as a dictionary of name-value pairs.
    :param labels: Labels to apply to the deployment and pods.
    :param limits: Resource limits as a dictionary (e.g., {"cpu": "100m", "memory": "128Mi"}).
    :param requests: Resource requests as a dictionary (e.g., {"cpu": "100m", "memory": "128Mi"}).
    :return: The JSON representation of the created deployment.
    """
    try:
        # Set default namespace if not provided
        if not namespace:
            namespace = "default"

        # Set default labels if not provided
        if not labels:
            labels = {"app": name}
        elif labels is None:
            labels = {"app": name}

        # Create the container
        container = client.V1Container(
            name=name,
            image=image,
            ports=[client.V1ContainerPort(container_port=int(port))] if port else None,
        )

        # Add environment variables if provided
        if env:
            env_list = []
            for key, value in env.items():
                env_list.append(client.V1EnvVar(name=key, value=str(value)))
            container.env = env_list

        # Add resource limits and requests if provided
        if limits or requests:
            # Ensure limits and requests are dictionaries
            if limits is None:
                limits = {}
            if requests is None:
                requests = {}

            container.resources = client.V1ResourceRequirements(
                limits=limits, requests=requests
            )

        # Create the pod template
        template = client.V1PodTemplateSpec(
            metadata=client.V1ObjectMeta(labels=labels),
            spec=client.V1PodSpec(containers=[container]),
        )

        # Create the deployment spec
        spec = client.V1DeploymentSpec(
            replicas=int(replicas),
            selector=client.V1LabelSelector(match_labels=labels),
            template=template,
        )

        # Create the deployment
        deployment = client.V1Deployment(
            api_version="apps/v1",
            kind="Deployment",
            metadata=client.V1ObjectMeta(name=name, namespace=namespace, labels=labels),
            spec=spec,
        )

        # Create the deployment in the cluster
        apps_v1 = client.AppsV1Api()
        result = apps_v1.create_namespaced_deployment(
            namespace=namespace, body=deployment
        )

        return json.dumps(result.to_dict(), indent=2, cls=DateTimeEncoder)

    except Exception as exc:
        return "Error:\n" + str(exc)


async def k8s_expose(
    resource_type,
    resource_name,
    port,
    target_port=None,
    name=None,
    protocol="TCP",
    type="ClusterIP",
    namespace=None,
    labels=None,
    selector=None,
):
    """
    Expose a resource as a new Kubernetes service.

    :param resource_type: The type of resource to expose (e.g., deployment, pod, replicaset, service).
    :param resource_name: The name of the resource to expose.
    :param port: The port that the service should serve on.
    :param target_port: The port on the resource that the service should direct traffic to.
    :param name: The name for the new service. If not specified, the resource name is used.
    :param protocol: The network protocol for the service. Default is TCP.
    :param type: The type of service to create (ClusterIP, NodePort, LoadBalancer). Default is ClusterIP.
    :param namespace: The namespace of the resource. If not specified, uses the default namespace.
    :param labels: Labels to apply to the service.
    :param selector: Selector for the service. If not specified, uses the resource's labels.
    :return: The JSON representation of the created service.
    """
    try:
        # Set default namespace if not provided
        if not namespace:
            namespace = "default"

        # Set default name if not provided
        if not name:
            name = resource_name

        # Set default target_port if not provided
        if not target_port:
            target_port = port

        # Get the API client
        api_client = client.ApiClient()
        dyn = dynamic.DynamicClient(api_client)

        # Find the resource to expose
        resource_found = False
        resource_labels = {}

        # Try to find the resource in different API groups
        for group, version in _get_group_versions(api_client):
            path = f"/api/{version}" if group == "" else f"/apis/{group}/{version}"
            try:
                reslist = api_client.call_api(
                    path, "GET", response_type="object", _return_http_data_only=True
                )
            except client.exceptions.ApiException:
                continue  # Skip if no permission or API not available

            for r in reslist["resources"]:
                if (
                    r.get("name") == f"{resource_type}s"
                    or r.get("name") == resource_type
                ):
                    gv = version if group == "" else f"{group}/{version}"
                    rc = dyn.resources.get(api_version=gv, kind=r["kind"])

                    try:
                        # Get the resource to expose
                        resource_obj = rc.get(name=resource_name, namespace=namespace)
                        resource_found = True

                        # Get the resource's labels for selector if not provided
                        if (
                            not selector
                            and hasattr(resource_obj, "metadata")
                            and hasattr(resource_obj.metadata, "labels")
                        ):
                            resource_labels = resource_obj.metadata.labels
                        break
                    except Exception:
                        continue

            if resource_found:
                break

        if not resource_found:
            return f"Error: resource '{resource_type}/{resource_name}' not found in namespace '{namespace}'"

        # Use resource labels as selector if not provided
        if not selector:
            selector = resource_labels

        # Ensure selector is a dictionary
        if selector is None:
            selector = {}

        # Create the service
        v1 = client.CoreV1Api()
        service_spec = client.V1ServiceSpec(
            selector=selector,
            ports=[
                client.V1ServicePort(
                    port=int(port), target_port=int(target_port), protocol=protocol
                )
            ],
            type=type,
        )

        service_metadata = client.V1ObjectMeta(
            name=name, namespace=namespace, labels=labels or {}
        )

        service = client.V1Service(
            api_version="v1",
            kind="Service",
            metadata=service_metadata,
            spec=service_spec,
        )

        # Create the service in the cluster
        result = v1.create_namespaced_service(namespace=namespace, body=service)

        return json.dumps(result.to_dict(), indent=2, cls=DateTimeEncoder)

    except Exception as exc:
        return "Error:\n" + str(exc)
