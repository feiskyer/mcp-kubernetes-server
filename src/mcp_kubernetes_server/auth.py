# -*- coding: utf-8 -*-
# pylint: disable=broad-exception-caught
import json

from kubernetes import client
from kubernetes.config import kube_config


async def k8s_auth_whoami():
    """
    Show the subject that you are currently authenticated as.

    :return: The current user information.
    """
    try:
        # Get the user info using the Kubernetes Python SDK
        try:
            # Get the user info
            user_info = {}

            # Get the configuration
            config = client.Configuration.get_default_copy()

            # Get the user info from the configuration
            if hasattr(config, "username") and config.username:
                user_info["username"] = config.username

            if hasattr(config, "client_certificate") and config.client_certificate:
                user_info["client_certificate"] = config.client_certificate

            # Get the token if available
            if hasattr(config, "api_key") and config.api_key:
                user_info["token"] = "present"

            # Get the current context

            current_context = kube_config.list_kube_config_contexts()[1]

            # Add the context info
            user_info["context"] = {
                "name": current_context["name"],
                "cluster": current_context["context"]["cluster"],
                "user": current_context["context"]["user"],
            }

            return json.dumps(user_info, indent=2)

        except Exception as e:
            return f"Error: {str(e)}"
    except Exception as exc:
        return "Error:\n" + str(exc)


async def k8s_auth_can_i(verb, resource, subresource=None, namespace=None, name=None):
    """
    Check whether an action is allowed.

    :param verb: The verb to check (e.g., get, list, create, update, delete).
    :param resource: The resource to check (e.g., pods, deployments).
    :param subresource: The subresource to check (e.g., log, status).
    :param namespace: The namespace to check in. If not specified, checks in the default namespace.
    :param name: The name of the resource to check.
    :return: Whether the action is allowed.
    """
    try:
        # Set default namespace if not provided
        if not namespace:
            namespace = "default"

        # Check using the Kubernetes Python SDK
        try:
            # Get the API client
            auth_v1 = client.AuthorizationV1Api()

            # Create the self subject access review
            sar = client.V1SelfSubjectAccessReview(
                spec=client.V1SelfSubjectAccessReviewSpec(
                    resource_attributes=client.V1ResourceAttributes(
                        namespace=namespace,
                        verb=verb,
                        resource=resource,
                        subresource=subresource,
                        name=name,
                    )
                )
            )

            # Check the access
            response = auth_v1.create_self_subject_access_review(sar)

            return {"allowed": response.status.allowed}

        except Exception as e:
            return f"Error: {str(e)}"
    except Exception as exc:
        return "Error:\n" + str(exc)
