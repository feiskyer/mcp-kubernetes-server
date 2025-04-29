# -*- coding: utf-8 -*-
# pylint: disable=broad-exception-caught
import json
from datetime import datetime
from kubernetes import client, dynamic


def _match(res, target):
    return (
        target == res.get("name")
        or target == res.get("singularName")
        or target in (res.get("shortNames") or [])
    )


def _get_group_versions(api_client):
    """
    Generator yielding ('', 'v1') for core, then ('apps', 'v1'), …
    Works no matter which SDK version you have.
    """
    # core
    yield "", "v1"

    # /apis – list API groups
    resp = api_client.call_api(
        "/apis", "GET", response_type="object", _return_http_data_only=True
    )
    for g in resp["groups"]:
        for v in g["versions"]:
            yield g["name"], v["version"]


class DateTimeEncoder(json.JSONEncoder):
    """
    Custom JSON encoder to handle datetime objects.
    """

    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()
        return super().default(o)


async def k8s_get(resource, name, namespace):
    """
    Fetch any Kubernetes object (or list) as JSON string. Pass name="" to list the collection and namespace="" to get the resource in all namespaces.

    :param resource: The resource type (e.g., pods, deployments).
    :param name: The name of the resource.
    :param namespace: The namespace of the resource.
    :return: The JSON representation of the resource.
    """
    try:
        api_client = client.ApiClient()
        dyn = dynamic.DynamicClient(api_client)

        rc = None  # dynamic.Resource we will eventually find

        # 2. iterate every group/version, read its /…/resources list
        for group, version in _get_group_versions(api_client):
            # discover resources for that gv
            path = f"/api/{version}" if group == "" else f"/apis/{group}/{version}"
            try:
                reslist = api_client.call_api(
                    path, "GET", response_type="object", _return_http_data_only=True
                )
            except client.exceptions.ApiException:
                continue  # disabled / no permission → skip

            for r in reslist["resources"]:
                if _match(r, resource):
                    gv = version if group == "" else f"{group}/{version}"
                    rc = dyn.resources.get(api_version=gv, kind=r["kind"])
                    break
            if rc:
                break

        if rc is None:
            return f"Error: resource '{resource}' not found in cluster"

        # 3. GET the object or list
        if rc.namespaced:
            if name:
                fetched = rc.get(name=name, namespace=namespace or "default")
            else:
                if namespace == "" or namespace is None:
                    fetched = rc.get(all_namespaces=True)
                else:
                    fetched = rc.get(namespace=namespace)
        else:
            fetched = rc.get(name=name) if name else rc.get()

        return json.dumps(fetched.to_dict(), indent=2, cls=DateTimeEncoder)

    except Exception as exc:
        return "Error:\n" + str(exc)


async def k8s_apis():
    """List all available APIs in the Kubernetes cluster."""
    result = client.ApisApi().get_api_versions(async_req=True).get()
    return json.dumps(result.to_dict(), indent=2)


async def k8s_crds():
    """List all Custom Resource Definitions (CRDs) in the Kubernetes cluster."""
    result = (
        client.ApiextensionsV1Api()
        .list_custom_resource_definition(async_req=True)
        .get()
    )
    return json.dumps(result.to_dict(), indent=2, cls=DateTimeEncoder)
