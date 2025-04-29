# -*- coding: utf-8 -*-
# pylint: disable=broad-exception-caught
import json

from kubernetes import client, dynamic

from .get import _get_group_versions, DateTimeEncoder


async def k8s_set_resources(
    resource_type,
    resource_name,
    namespace=None,
    containers=None,
    limits=None,
    requests=None,
):
    """
    Set resource limits and requests for containers in a pod, deployment, etc.

    :param resource_type: The type of resource to modify (e.g., deployment, pod, statefulset).
    :param resource_name: The name of the resource to modify.
    :param namespace: The namespace of the resource. If not specified, uses the default namespace.
    :param containers: List of container names to modify. If None, modifies all containers.
    :param limits: Resource limits as a dictionary (e.g., {"cpu": "100m", "memory": "128Mi"}).
    :param requests: Resource requests as a dictionary (e.g., {"cpu": "100m", "memory": "128Mi"}).
    :return: The JSON representation of the modified resource.
    """
    try:
        # Set default namespace if not provided
        if not namespace:
            namespace = "default"

        # Get the API client
        api_client = client.ApiClient()
        dyn = dynamic.DynamicClient(api_client)

        # Find the resource to modify
        resource_found = False
        resource_obj = None

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
                        # Get the resource to modify
                        resource_obj = rc.get(name=resource_name, namespace=namespace)
                        resource_found = True
                        break
                    except Exception:
                        continue

            if resource_found:
                break

        if not resource_found or not resource_obj:
            return f"Error: resource '{resource_type}/{resource_name}' not found in namespace '{namespace}'"

        # Modify the resource
        resource_dict = resource_obj.to_dict()

        # Handle different resource types
        if resource_type.lower() in [
            "deployment",
            "statefulset",
            "daemonset",
            "replicaset",
        ]:
            # For workload controllers, modify the pod template
            if (
                "spec" in resource_dict
                and "template" in resource_dict["spec"]
                and "spec" in resource_dict["spec"]["template"]
            ):
                pod_spec = resource_dict["spec"]["template"]["spec"]
                if "containers" in pod_spec:
                    for container in pod_spec["containers"]:
                        # If containers list is provided, only modify those containers
                        if containers and container["name"] not in containers:
                            continue

                        # Set resources
                        if "resources" not in container:
                            container["resources"] = {}

                        # Ensure limits and requests are dictionaries
                        if limits is not None:
                            container["resources"]["limits"] = limits

                        if requests is not None:
                            container["resources"]["requests"] = requests
        elif resource_type.lower() == "pod":
            # For pods, modify the containers directly
            if "spec" in resource_dict and "containers" in resource_dict["spec"]:
                for container in resource_dict["spec"]["containers"]:
                    # If containers list is provided, only modify those containers
                    if containers and container["name"] not in containers:
                        continue

                    # Set resources
                    if "resources" not in container:
                        container["resources"] = {}

                    if limits is not None:
                        container["resources"]["limits"] = limits

                    if requests is not None:
                        container["resources"]["requests"] = requests
        else:
            return f"Error: resource type '{resource_type}' does not support setting resources"

        # Update the resource
        result = rc.replace(body=resource_dict, name=resource_name, namespace=namespace)

        return json.dumps(result.to_dict(), indent=2, cls=DateTimeEncoder)

    except Exception as exc:
        return "Error:\n" + str(exc)


async def k8s_set_image(resource_type, resource_name, container, image, namespace=None):
    """
    Set the image for a container in a pod, deployment, etc.

    :param resource_type: The type of resource to modify (e.g., deployment, pod, statefulset).
    :param resource_name: The name of the resource to modify.
    :param container: The name of the container to modify.
    :param image: The new image to use.
    :param namespace: The namespace of the resource. If not specified, uses the default namespace.
    :return: The JSON representation of the modified resource.
    """
    try:
        # Set default namespace if not provided
        if not namespace:
            namespace = "default"

        # Get the API client
        api_client = client.ApiClient()
        dyn = dynamic.DynamicClient(api_client)

        # Find the resource to modify
        resource_found = False
        resource_obj = None

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
                        # Get the resource to modify
                        resource_obj = rc.get(name=resource_name, namespace=namespace)
                        resource_found = True
                        break
                    except Exception:
                        continue

            if resource_found:
                break

        if not resource_found or not resource_obj:
            return f"Error: resource '{resource_type}/{resource_name}' not found in namespace '{namespace}'"

        # Modify the resource
        resource_dict = resource_obj.to_dict()
        container_found = False

        # Handle different resource types
        if resource_type.lower() in [
            "deployment",
            "statefulset",
            "daemonset",
            "replicaset",
        ]:
            # For workload controllers, modify the pod template
            if (
                "spec" in resource_dict
                and "template" in resource_dict["spec"]
                and "spec" in resource_dict["spec"]["template"]
            ):
                pod_spec = resource_dict["spec"]["template"]["spec"]
                if "containers" in pod_spec:
                    for c in pod_spec["containers"]:
                        if c["name"] == container:
                            c["image"] = image
                            container_found = True
                            break
        elif resource_type.lower() == "pod":
            # For pods, modify the containers directly
            if "spec" in resource_dict and "containers" in resource_dict["spec"]:
                for c in resource_dict["spec"]["containers"]:
                    if c["name"] == container:
                        c["image"] = image
                        container_found = True
                        break
        else:
            return (
                f"Error: resource type '{resource_type}' does not support setting image"
            )

        if not container_found:
            return f"Error: container '{container}' not found in resource '{resource_type}/{resource_name}'"

        # Update the resource
        result = rc.replace(body=resource_dict, name=resource_name, namespace=namespace)

        return json.dumps(result.to_dict(), indent=2, cls=DateTimeEncoder)

    except Exception as exc:
        return "Error:\n" + str(exc)


async def k8s_set_env(
    resource_type, resource_name, container, env_dict, namespace=None
):
    """
    Set environment variables for a container in a pod, deployment, etc.

    :param resource_type: The type of resource to modify (e.g., deployment, pod, statefulset).
    :param resource_name: The name of the resource to modify.
    :param container: The name of the container to modify.
    :param env_dict: Dictionary of environment variables to set.
    :param namespace: The namespace of the resource. If not specified, uses the default namespace.
    :return: The JSON representation of the modified resource.
    """
    try:
        # Set default namespace if not provided
        if not namespace:
            namespace = "default"

        # Get the API client
        api_client = client.ApiClient()
        dyn = dynamic.DynamicClient(api_client)

        # Find the resource to modify
        resource_found = False
        resource_obj = None

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
                        # Get the resource to modify
                        resource_obj = rc.get(name=resource_name, namespace=namespace)
                        resource_found = True
                        break
                    except Exception:
                        continue

            if resource_found:
                break

        if not resource_found or not resource_obj:
            return f"Error: resource '{resource_type}/{resource_name}' not found in namespace '{namespace}'"

        # Modify the resource
        resource_dict = resource_obj.to_dict()
        container_found = False

        # Handle different resource types
        if resource_type.lower() in [
            "deployment",
            "statefulset",
            "daemonset",
            "replicaset",
        ]:
            # For workload controllers, modify the pod template
            if (
                "spec" in resource_dict
                and "template" in resource_dict["spec"]
                and "spec" in resource_dict["spec"]["template"]
            ):
                pod_spec = resource_dict["spec"]["template"]["spec"]
                if "containers" in pod_spec:
                    for c in pod_spec["containers"]:
                        if c["name"] == container:
                            # Initialize env if it doesn't exist
                            if "env" not in c:
                                c["env"] = []

                            # Update or add environment variables
                            for key, value in env_dict.items():
                                # Check if the env var already exists
                                env_var_found = False
                                for env_var in c["env"]:
                                    if env_var["name"] == key:
                                        env_var["value"] = str(value)
                                        env_var_found = True
                                        break

                                # Add the env var if it doesn't exist
                                if not env_var_found:
                                    c["env"].append({"name": key, "value": str(value)})

                            container_found = True
                            break
        elif resource_type.lower() == "pod":
            # For pods, modify the containers directly
            if "spec" in resource_dict and "containers" in resource_dict["spec"]:
                for c in resource_dict["spec"]["containers"]:
                    if c["name"] == container:
                        # Initialize env if it doesn't exist
                        if "env" not in c:
                            c["env"] = []

                        # Update or add environment variables
                        for key, value in env_dict.items():
                            # Check if the env var already exists
                            env_var_found = False
                            for env_var in c["env"]:
                                if env_var["name"] == key:
                                    env_var["value"] = str(value)
                                    env_var_found = True
                                    break

                            # Add the env var if it doesn't exist
                            if not env_var_found:
                                c["env"].append({"name": key, "value": str(value)})

                        container_found = True
                        break
        else:
            return f"Error: resource type '{resource_type}' does not support setting environment variables"

        if not container_found:
            return f"Error: container '{container}' not found in resource '{resource_type}/{resource_name}'"

        # Update the resource
        result = rc.replace(body=resource_dict, name=resource_name, namespace=namespace)

        return json.dumps(result.to_dict(), indent=2, cls=DateTimeEncoder)

    except Exception as exc:
        return "Error:\n" + str(exc)
