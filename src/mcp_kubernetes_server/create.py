# -*- coding: utf-8 -*-
# pylint: disable=broad-exception-caught
import io
import json

import yaml
from kubernetes import client
from kubernetes.utils import create_from_yaml

from .get import DateTimeEncoder


def _create(yaml_content, namespace=None, apply=False):
    try:
        # Parse the YAML content - convert string to stream for safe_load_all
        yaml_objects = list(yaml.safe_load_all(io.StringIO(yaml_content)))
        if not yaml_objects:
            return "Error: No valid YAML/JSON content provided"

        api_client = client.ApiClient()
        results = []

        for yaml_object in yaml_objects:
            if not yaml_object:
                continue

            # If namespace is provided, override the namespace in the YAML
            if namespace and "metadata" in yaml_object:
                yaml_object["metadata"]["namespace"] = namespace

            # Create the resource
            try:
                resource = create_from_yaml(api_client, yaml_objects=[yaml_object], apply=apply)
                if isinstance(resource, list):
                    for item in resource:
                        if hasattr(item, "to_dict"):
                            results.append(item.to_dict())
                        else:
                            results.append({"status": "created", "object": str(item)})
                elif hasattr(resource, "to_dict"):
                    results.append(resource.to_dict())
                else:
                    results.append({"status": "created", "object": str(resource)})
            except Exception as e:
                results.append(
                    {"status": "error", "message": str(e), "object": yaml_object}
                )

        return json.dumps(results, indent=2, cls=DateTimeEncoder)

    except Exception as exc:
        return "Error:\n" + str(exc)


async def k8s_create(yaml_content, namespace=None):
    """
    Create a Kubernetes resource from YAML/JSON content.

    :param yaml_content: The YAML or JSON content of the resource to create.
    :param namespace: The namespace to create the resource in. If not provided, uses the namespace in the YAML or the default namespace.
    :return: The JSON representation of the created resource.
    """
    return _create(yaml_content=yaml_content, namespace=namespace)


async def k8s_apply(yaml_content=None, namespace=None):
    """
    Apply a configuration to a resource by file content or file path.

    :param yaml_content: The YAML content to apply.
    :param namespace: The namespace to apply the configuration to. If not specified, uses the default namespace.
    :return: The result of the apply operation.
    """
    return _create(yaml_content=yaml_content, namespace=namespace, apply=True)
