# -*- coding: utf-8 -*-
# pylint: disable=broad-exception-caught
from kubernetes import client, dynamic
from .get import _get_group_versions


async def k8s_describe(
    resource_type, name=None, namespace=None, selector=None, all_namespaces=False
):
    """
    Show detailed information about a specific resource or group of resources.

    :param resource_type: The type of resource to describe (e.g., pods, deployments).
    :param name: The name of the resource to describe. If not specified, describes resources matching the selector.
    :param namespace: The namespace of the resource. If not specified, uses the default namespace.
    :param selector: Label selector to filter resources (e.g., "app=nginx").
    :param all_namespaces: Whether to describe resources in all namespaces.
    :return: The detailed description of the resource(s).
    """
    try:
        # Set default namespace if not provided and not all namespaces
        if not namespace and not all_namespaces:
            namespace = "default"

        # Get the description using the Kubernetes Python SDK
        try:
            # Get the API client
            api_client = client.ApiClient()
            dyn = dynamic.DynamicClient(api_client)

            # Find the resource to describe
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
                        resource_client = dyn.resources.get(
                            api_version=gv, kind=r["kind"]
                        )
                        resource_found = True
                        break

                if resource_found:
                    break

            if not resource_found or not resource_client:
                return f"Error: resource type '{resource_type}' not found"

            # Get the resource(s)
            if name:
                if all_namespaces:
                    # Need to find the namespace first
                    all_resources = resource_client.get(label_selector=selector)
                    resource = None

                    for item in all_resources.items:
                        if item.metadata.name == name:
                            resource = item
                            break

                    if not resource:
                        return f"Error: {resource_type} '{name}' not found in any namespace"
                else:
                    resource = resource_client.get(name=name, namespace=namespace)

                # Format the description
                description = _format_resource_description(resource)

                # Get events related to this resource
                core_v1 = client.CoreV1Api()
                field_selector = f"involvedObject.name={name}"

                # Check if the resource has a namespace attribute and it's not None or empty
                has_namespace = (hasattr(resource.metadata, "namespace") and
                                resource.metadata.namespace is not None and
                                resource.metadata.namespace != "")

                if has_namespace:
                    field_selector += (
                        f",involvedObject.namespace={resource.metadata.namespace}"
                    )
                    events = core_v1.list_namespaced_event(
                        namespace=resource.metadata.namespace,
                        field_selector=field_selector,
                    )
                else:
                    # For non-namespaced resources like nodes, use list_event_for_all_namespaces
                    events = core_v1.list_event_for_all_namespaces(
                        field_selector=field_selector
                    )

                # Add events to the description
                if events.items:
                    description += "\nEvents:\n"
                    for event in events.items:
                        description += f"  {event.last_timestamp}: {event.type} {event.reason}: {event.message}\n"

                return description
            else:
                # Get all resources matching the selector
                if all_namespaces:
                    resources = resource_client.get(label_selector=selector)
                else:
                    resources = resource_client.get(
                        namespace=namespace, label_selector=selector
                    )

                # Format the descriptions
                descriptions = []
                for resource in resources.items:
                    descriptions.append(_format_resource_description(resource))

                    # Get events related to this resource
                    core_v1 = client.CoreV1Api()
                    field_selector = f"involvedObject.name={resource.metadata.name}"

                    # Check if the resource has a namespace attribute and it's not None or empty
                    has_namespace = (hasattr(resource.metadata, "namespace") and
                                    resource.metadata.namespace is not None and
                                    resource.metadata.namespace != "")

                    if has_namespace:
                        field_selector += (
                            f",involvedObject.namespace={resource.metadata.namespace}"
                        )
                        events = core_v1.list_namespaced_event(
                            namespace=resource.metadata.namespace,
                            field_selector=field_selector,
                        )
                    else:
                        # For non-namespaced resources like nodes, use list_event_for_all_namespaces
                        events = core_v1.list_event_for_all_namespaces(
                            field_selector=field_selector
                        )

                    # Add events to the description
                    if events.items:
                        descriptions[-1] += "\nEvents:\n"
                        for event in events.items:
                            descriptions[
                                -1
                            ] += f"  {event.last_timestamp}: {event.type} {event.reason}: {event.message}\n"

                return (
                    "\n\n".join(descriptions)
                    if descriptions
                    else f"No {resource_type} found"
                )

        except Exception as e:
            return f"Error: {str(e)}"
    except Exception as exc:
        return "Error:\n" + str(exc)


def _format_resource_description(resource):
    """
    Format a resource object into a human-readable description.

    :param resource: The resource object to format.
    :return: A string containing the formatted description.
    """
    # Start with the resource kind and name
    kind = resource.kind if hasattr(resource, "kind") else "Resource"
    description = f"{kind}: {resource.metadata.name}\n"

    # Add namespace if available
    if hasattr(resource.metadata, "namespace"):
        description += f"Namespace: {resource.metadata.namespace}\n"

    # Add labels if available
    if hasattr(resource.metadata, "labels") and resource.metadata.labels:
        description += "Labels:\n"
        for key, value in resource.metadata.labels.items():
            description += f"  {key}={value}\n"

    # Add annotations if available
    if hasattr(resource.metadata, "annotations") and resource.metadata.annotations:
        description += "Annotations:\n"
        for key, value in resource.metadata.annotations.items():
            description += f"  {key}={value}\n"

    # Add creation timestamp
    if hasattr(resource.metadata, "creation_timestamp"):
        description += f"Creation Timestamp: {resource.metadata.creation_timestamp}\n"

    # Add resource-specific details
    if kind.lower() == "pod":
        # Add pod status
        description += f"Status: {resource.status.phase}\n"

        # Add pod IP
        if hasattr(resource.status, "pod_ip") and resource.status.pod_ip:
            description += f"IP: {resource.status.pod_ip}\n"

        # Add node name
        if hasattr(resource.spec, "node_name") and resource.spec.node_name:
            description += f"Node: {resource.spec.node_name}\n"

        # Add containers
        if hasattr(resource.spec, "containers"):
            description += "Containers:\n"
            for container in resource.spec.containers:
                description += f"  {container.name}:\n"
                description += f"    Image: {container.image}\n"

                # Add ports
                if hasattr(container, "ports") and container.ports:
                    description += "    Ports:\n"
                    for port in container.ports:
                        description += f"      {port.container_port}/{port.protocol}\n"

                # Add environment variables
                if hasattr(container, "env") and container.env:
                    description += "    Environment:\n"
                    for env in container.env:
                        value = (
                            env.value
                            if hasattr(env, "value") and env.value
                            else "<set to the key in a secret>"
                        )
                        description += f"      {env.name}={value}\n"

                # Add volume mounts
                if hasattr(container, "volume_mounts") and container.volume_mounts:
                    description += "    Mounts:\n"
                    for mount in container.volume_mounts:
                        description += f"      {mount.name} -> {mount.mount_path}\n"

        # Add volumes
        if hasattr(resource.spec, "volumes") and resource.spec.volumes:
            description += "Volumes:\n"
            for volume in resource.spec.volumes:
                description += f"  {volume.name}:\n"

                # Add volume source details
                if hasattr(volume, "host_path") and volume.host_path:
                    description += "    Type: HostPath\n"
                    description += f"    Path: {volume.host_path.path}\n"
                elif (
                    hasattr(volume, "persistent_volume_claim")
                    and volume.persistent_volume_claim
                ):
                    description += "    Type: PersistentVolumeClaim\n"
                    description += (
                        f"    Claim Name: {volume.persistent_volume_claim.claim_name}\n"
                    )
                elif hasattr(volume, "config_map") and volume.config_map:
                    description += "    Type: ConfigMap\n"
                    description += f"    Name: {volume.config_map.name}\n"
                elif hasattr(volume, "secret") and volume.secret:
                    description += "    Type: Secret\n"
                    description += f"    Secret Name: {volume.secret.secret_name}\n"

    elif kind.lower() == "deployment":
        # Add replicas
        if hasattr(resource.spec, "replicas"):
            description += f"Replicas: {resource.spec.replicas}\n"

        # Add selector
        if hasattr(resource.spec, "selector") and hasattr(
            resource.spec.selector, "match_labels"
        ):
            description += "Selector:\n"
            for key, value in resource.spec.selector.match_labels.items():
                description += f"  {key}={value}\n"

        # Add strategy
        if hasattr(resource.spec, "strategy") and hasattr(
            resource.spec.strategy, "type"
        ):
            description += f"Strategy: {resource.spec.strategy.type}\n"

        # Add status
        if hasattr(resource.status, "available_replicas"):
            description += (
                f"Available Replicas: {resource.status.available_replicas or 0}\n"
            )
        if hasattr(resource.status, "ready_replicas"):
            description += f"Ready Replicas: {resource.status.ready_replicas or 0}\n"
        if hasattr(resource.status, "updated_replicas"):
            description += (
                f"Updated Replicas: {resource.status.updated_replicas or 0}\n"
            )

    elif kind.lower() == "node":
        # Add node status
        if hasattr(resource.status, "conditions"):
            description += "Conditions:\n"
            for condition in resource.status.conditions:
                description += f"  {condition.type}: {condition.status}\n"
                if hasattr(condition, "reason") and condition.reason:
                    description += f"    Reason: {condition.reason}\n"
                if hasattr(condition, "message") and condition.message:
                    description += f"    Message: {condition.message}\n"

        # Add node capacity
        if hasattr(resource.status, "capacity"):
            description += "Capacity:\n"
            for resource_name, quantity in resource.status.capacity.items():
                description += f"  {resource_name}: {quantity}\n"

        # Add node allocatable
        if hasattr(resource.status, "allocatable"):
            description += "Allocatable:\n"
            for resource_name, quantity in resource.status.allocatable.items():
                description += f"  {resource_name}: {quantity}\n"

        # Add node addresses
        if hasattr(resource.status, "addresses"):
            description += "Addresses:\n"
            for address in resource.status.addresses:
                description += f"  {address.type}: {address.address}\n"

        # Add node info
        if hasattr(resource.status, "node_info"):
            description += "System Info:\n"
            node_info = resource.status.node_info
            if hasattr(node_info, "kernel_version"):
                description += f"  Kernel Version: {node_info.kernel_version}\n"
            if hasattr(node_info, "os_image"):
                description += f"  OS Image: {node_info.os_image}\n"
            if hasattr(node_info, "container_runtime_version"):
                description += f"  Container Runtime: {node_info.container_runtime_version}\n"
            if hasattr(node_info, "kubelet_version"):
                description += f"  Kubelet Version: {node_info.kubelet_version}\n"
            if hasattr(node_info, "kube_proxy_version"):
                description += f"  Kube-Proxy Version: {node_info.kube_proxy_version}\n"

        # Add unschedulable status
        if hasattr(resource.spec, "unschedulable") and resource.spec.unschedulable:
            description += "Unschedulable: True (Node is cordoned)\n"

    elif kind.lower() == "service":
        # Add type
        if hasattr(resource.spec, "type"):
            description += f"Type: {resource.spec.type}\n"

        # Add cluster IP
        if hasattr(resource.spec, "cluster_ip"):
            description += f"Cluster IP: {resource.spec.cluster_ip}\n"

        # Add external IPs
        if hasattr(resource.spec, "external_i_ps") and resource.spec.external_i_ps:
            description += f"External IPs: {', '.join(resource.spec.external_i_ps)}\n"

        # Add ports
        if hasattr(resource.spec, "ports") and resource.spec.ports:
            description += "Ports:\n"
            for port in resource.spec.ports:
                port_desc = f"  {port.port}/{port.protocol}"
                if hasattr(port, "target_port"):
                    port_desc += f" -> {port.target_port}"
                if hasattr(port, "node_port") and port.node_port:
                    port_desc += f" (NodePort: {port.node_port})"
                description += port_desc + "\n"

        # Add selector
        if hasattr(resource.spec, "selector") and resource.spec.selector:
            description += "Selector:\n"
            for key, value in resource.spec.selector.items():
                description += f"  {key}={value}\n"

    # Add other resource-specific details as needed

    return description
