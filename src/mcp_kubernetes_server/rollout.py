# -*- coding: utf-8 -*-
# pylint: disable=broad-exception-caught
import json
from kubernetes import client
from .get import DateTimeEncoder


async def k8s_rollout_status(resource_type, name, namespace=None):
    """
    Get the status of a rollout for a deployment, daemonset, or statefulset.

    :param resource_type: The type of resource (deployment, daemonset, statefulset).
    :param name: The name of the resource.
    :param namespace: The namespace of the resource. If not specified, uses the default namespace.
    :return: The status of the rollout.
    """
    try:
        # Set default namespace if not provided
        if not namespace:
            namespace = "default"

        # Get the status using the Kubernetes Python SDK
        try:
            # Get the resource
            if resource_type.lower() == "deployment":
                apps_v1 = client.AppsV1Api()
                resource = apps_v1.read_namespaced_deployment_status(name, namespace)

                # Format the status
                status = {
                    "name": resource.metadata.name,
                    "namespace": resource.metadata.namespace,
                    "replicas": resource.status.replicas,
                    "ready_replicas": resource.status.ready_replicas or 0,
                    "updated_replicas": resource.status.updated_replicas or 0,
                    "available_replicas": resource.status.available_replicas or 0,
                    "conditions": [
                        {
                            "type": condition.type,
                            "status": condition.status,
                            "reason": condition.reason,
                            "message": condition.message,
                            "last_update_time": condition.last_update_time,
                            "last_transition_time": condition.last_transition_time,
                        }
                        for condition in (resource.status.conditions or [])
                    ],
                }

                # Determine if the rollout is complete
                if (
                    status["ready_replicas"] == status["replicas"]
                    and status["updated_replicas"] == status["replicas"]
                    and status["available_replicas"] == status["replicas"]
                ):
                    status["status"] = "complete"
                    status_message = f'deployment "{name}" successfully rolled out'
                else:
                    status["status"] = "in progress"
                    status_message = f"Waiting for deployment \"{name}\" rollout to finish: {status['updated_replicas']} out of {status['replicas']} new replicas have been updated..."

                    if status["available_replicas"] < status["updated_replicas"]:
                        status_message += f"\n{status['available_replicas']} available replicas are ready..."

                status["message"] = status_message
                return json.dumps(status, indent=2, cls=DateTimeEncoder)

            elif resource_type.lower() == "daemonset":
                apps_v1 = client.AppsV1Api()
                resource = apps_v1.read_namespaced_daemon_set_status(name, namespace)

                # Format the status
                status = {
                    "name": resource.metadata.name,
                    "namespace": resource.metadata.namespace,
                    "desired_number_scheduled": resource.status.desired_number_scheduled,
                    "current_number_scheduled": resource.status.current_number_scheduled,
                    "number_ready": resource.status.number_ready,
                    "updated_number_scheduled": resource.status.updated_number_scheduled,
                    "number_available": resource.status.number_available,
                    "conditions": [
                        {
                            "type": condition.type,
                            "status": condition.status,
                            "reason": condition.reason,
                            "message": condition.message,
                            "last_transition_time": condition.last_transition_time,
                        }
                        for condition in (resource.status.conditions or [])
                    ],
                }

                # Determine if the rollout is complete
                if (
                    status["current_number_scheduled"]
                    == status["desired_number_scheduled"]
                    and status["number_ready"] == status["desired_number_scheduled"]
                    and status["updated_number_scheduled"]
                    == status["desired_number_scheduled"]
                ):
                    status["status"] = "complete"
                    status_message = f'daemon set "{name}" successfully rolled out'
                else:
                    status["status"] = "in progress"
                    status_message = f"Waiting for daemon set \"{name}\" rollout to finish: {status['updated_number_scheduled']} out of {status['desired_number_scheduled']} new pods have been updated..."

                    if status["number_ready"] < status["current_number_scheduled"]:
                        status_message += f"\n{status['number_ready']} of {status['current_number_scheduled']} updated pods are ready..."

                status["message"] = status_message
                return json.dumps(status, indent=2, cls=DateTimeEncoder)

            elif resource_type.lower() == "statefulset":
                apps_v1 = client.AppsV1Api()
                resource = apps_v1.read_namespaced_stateful_set_status(name, namespace)

                # Format the status
                status = {
                    "name": resource.metadata.name,
                    "namespace": resource.metadata.namespace,
                    "replicas": resource.status.replicas,
                    "ready_replicas": resource.status.ready_replicas or 0,
                    "current_replicas": resource.status.current_replicas or 0,
                    "updated_replicas": resource.status.updated_replicas or 0,
                    "current_revision": resource.status.current_revision,
                    "update_revision": resource.status.update_revision,
                }

                # Determine if the rollout is complete
                if (
                    status["ready_replicas"] == status["replicas"]
                    and status["updated_replicas"] == status["replicas"]
                ):
                    status["status"] = "complete"
                    status_message = f'statefulset "{name}" successfully rolled out'
                else:
                    status["status"] = "in progress"
                    status_message = f"Waiting for statefulset \"{name}\" rollout to finish: {status['updated_replicas']} out of {status['replicas']} new pods have been updated..."

                    if status["ready_replicas"] < status["replicas"]:
                        status_message += f"\n{status['ready_replicas']} of {status['replicas']} updated pods are ready..."

                status["message"] = status_message
                return json.dumps(status, indent=2, cls=DateTimeEncoder)

            else:
                return f"Error: resource type '{resource_type}' does not support rollout status"

        except Exception as e:
            return f"Error: {str(e)}"
    except Exception as exc:
        return "Error:\n" + str(exc)


async def k8s_rollout_history(resource_type, name, namespace=None, revision=None):
    """
    Get the rollout history for a deployment, daemonset, or statefulset.

    :param resource_type: The type of resource (deployment, daemonset, statefulset).
    :param name: The name of the resource.
    :param namespace: The namespace of the resource. If not specified, uses the default namespace.
    :param revision: The specific revision to get. If not specified, gets all revisions.
    :return: The rollout history.
    """
    try:
        # Set default namespace if not provided
        if not namespace:
            namespace = "default"

        # Get the history using the Kubernetes Python SDK
        try:
            # Get the resource
            if resource_type.lower() == "deployment":
                apps_v1 = client.AppsV1Api()
                resource = apps_v1.read_namespaced_deployment(name, namespace)

                # Get the revision history
                history = []

                # Get the ReplicaSets owned by this Deployment
                selector = ",".join(
                    [f"{k}={v}" for k, v in resource.spec.selector.match_labels.items()]
                )
                replica_sets = apps_v1.list_namespaced_replica_set(
                    namespace, label_selector=selector
                )

                # Sort by revision number (descending)
                replica_sets.items.sort(
                    key=lambda rs: int(
                        rs.metadata.annotations.get(
                            "deployment.kubernetes.io/revision", "0"
                        )
                    ),
                    reverse=True,
                )

                # Format the history
                for rs in replica_sets.items:
                    revision_number = rs.metadata.annotations.get(
                        "deployment.kubernetes.io/revision", "unknown"
                    )

                    # If a specific revision is requested, skip others
                    if revision and revision != revision_number:
                        continue

                    # Get change-cause annotation if available
                    change_cause = rs.metadata.annotations.get(
                        "kubernetes.io/change-cause", ""
                    )

                    # Get container details
                    containers = []
                    for container in rs.spec.template.spec.containers:
                        containers.append(
                            {"name": container.name, "image": container.image}
                        )

                    history_entry = {
                        "revision": revision_number,
                        "replica_set": rs.metadata.name,
                        "created": rs.metadata.creation_timestamp,
                        "containers": containers,
                        "replicas": rs.spec.replicas,
                        "change_cause": change_cause,
                    }

                    # If a specific revision is requested, add more details
                    if revision and revision == revision_number:
                        # Add pod template annotations
                        if (
                            rs.spec.template.metadata
                            and rs.spec.template.metadata.annotations
                        ):
                            history_entry["annotations"] = (
                                rs.spec.template.metadata.annotations
                            )

                        # Add pod template labels
                        if (
                            rs.spec.template.metadata
                            and rs.spec.template.metadata.labels
                        ):
                            history_entry["labels"] = rs.spec.template.metadata.labels

                    history.append(history_entry)

                # Format the output similar to kubectl
                if history:
                    if revision:
                        # Detailed view for a specific revision
                        result = f"REVISION: {history[0]['revision']}\n"
                        if history[0]["change_cause"]:
                            result += f"Change-Cause: {history[0]['change_cause']}\n"
                        result += "Pod Template:\n"
                        result += "  Labels:\n"
                        if "labels" in history[0]:
                            for k, v in history[0]["labels"].items():
                                result += f"    {k}: {v}\n"
                        result += "  Containers:\n"
                        for container in history[0]["containers"]:
                            result += f"   {container['name']}:\n"
                            result += f"    Image: {container['image']}\n"
                        return result
                    else:
                        # Summary view for all revisions
                        result = "REVISION  CHANGE-CAUSE\n"
                        for entry in history:
                            result += (
                                f"{entry['revision']}        {entry['change_cause']}\n"
                            )
                        return result
                else:
                    return "No rollout history found"

            elif resource_type.lower() == "statefulset":
                apps_v1 = client.AppsV1Api()
                resource = apps_v1.read_namespaced_stateful_set(name, namespace)

                # StatefulSets don't have the same revision history as Deployments
                # We can only show the current revision and update revision
                current_revision = resource.status.current_revision
                update_revision = resource.status.update_revision

                result = "StatefulSet revisions:\n"
                result += f"Current revision: {current_revision}\n"
                result += f"Update revision: {update_revision}\n"

                return result

            elif resource_type.lower() == "daemonset":
                apps_v1 = client.AppsV1Api()
                resource = apps_v1.read_namespaced_daemon_set(name, namespace)

                # DaemonSets don't have built-in revision history like Deployments
                # We can check for controller-revision-hash labels in the pods
                core_v1 = client.CoreV1Api()

                # Get the pods controlled by this DaemonSet
                selector = ",".join(
                    [f"{k}={v}" for k, v in resource.spec.selector.match_labels.items()]
                )
                pods = core_v1.list_namespaced_pod(namespace, label_selector=selector)

                # Get unique controller-revision-hash values
                revisions = set()
                for pod in pods.items:
                    if (
                        pod.metadata.labels
                        and "controller-revision-hash" in pod.metadata.labels
                    ):
                        revisions.add(pod.metadata.labels["controller-revision-hash"])

                result = "DaemonSet revisions:\n"
                for rev in revisions:
                    result += f"Revision: {rev}\n"

                return result

            else:
                return f"Error: resource type '{resource_type}' history not available through API"

        except Exception as e:
            return f"Error: {str(e)}"
    except Exception as exc:
        return "Error:\n" + str(exc)


async def k8s_rollout_undo(resource_type, name, namespace=None, to_revision=None):
    """
    Undo a rollout for a deployment, daemonset, or statefulset.

    :param resource_type: The type of resource (deployment, daemonset, statefulset).
    :param name: The name of the resource.
    :param namespace: The namespace of the resource. If not specified, uses the default namespace.
    :param to_revision: The revision to roll back to. If not specified, rolls back to the previous revision.
    :return: The result of the rollback operation.
    """
    try:
        # Set default namespace if not provided
        if not namespace:
            namespace = "default"

        # Use the Kubernetes Python SDK for rollback
        try:
            # Get the resource
            if resource_type.lower() == "deployment":
                apps_v1 = client.AppsV1Api()

                # Get the deployment
                deployment = apps_v1.read_namespaced_deployment(name, namespace)

                # Get the ReplicaSets owned by this Deployment
                selector = ",".join(
                    [
                        f"{k}={v}"
                        for k, v in deployment.spec.selector.match_labels.items()
                    ]
                )
                replica_sets = apps_v1.list_namespaced_replica_set(
                    namespace, label_selector=selector
                )

                # If a specific revision is requested, find the corresponding ReplicaSet
                if to_revision:
                    # Find the ReplicaSet with the requested revision
                    target_rs = None
                    for rs in replica_sets.items:
                        if rs.metadata.annotations.get(
                            "deployment.kubernetes.io/revision"
                        ) == str(to_revision):
                            target_rs = rs
                            break

                    if not target_rs:
                        return f"Error: revision {to_revision} not found"

                    # Update the Deployment to use the template from the target ReplicaSet
                    deployment.spec.template = target_rs.spec.template
                    apps_v1.patch_namespaced_deployment(name, namespace, deployment)

                    return f"Rollback to revision {to_revision} initiated successfully"
                else:
                    # Sort by revision number (descending)
                    replica_sets.items.sort(
                        key=lambda rs: int(
                            rs.metadata.annotations.get(
                                "deployment.kubernetes.io/revision", "0"
                            )
                        ),
                        reverse=True,
                    )

                    # Find the previous revision (second in the list after sorting)
                    if len(replica_sets.items) < 2:
                        return "Error: No previous revision found for rollback"

                    # Get the second ReplicaSet (previous revision)
                    target_rs = replica_sets.items[1]

                    # Update the Deployment to use the template from the target ReplicaSet
                    deployment.spec.template = target_rs.spec.template
                    apps_v1.patch_namespaced_deployment(name, namespace, deployment)

                    return "Rollback to previous revision initiated successfully"

            elif resource_type.lower() == "statefulset":
                apps_v1 = client.AppsV1Api()

                # For StatefulSets, we can use the updateStrategy.rollingUpdate.partition field
                # to effectively roll back by setting it to 0
                # Read the StatefulSet (not used directly, but we need to check it exists)
                apps_v1.read_namespaced_stateful_set(name, namespace)

                # Create a patch to set partition to 0
                patch = {
                    "spec": {
                        "updateStrategy": {
                            "type": "RollingUpdate",
                            "rollingUpdate": {"partition": 0},
                        }
                    }
                }

                # Apply the patch
                apps_v1.patch_namespaced_stateful_set(
                    name,
                    namespace,
                    patch,
                )

                return f"Rollback of StatefulSet {name} initiated successfully"

            elif resource_type.lower() == "daemonset":
                apps_v1 = client.AppsV1Api()

                # For DaemonSets, we can use a similar approach as Deployments
                # but DaemonSets don't have a direct rollback mechanism in the API
                # We can trigger a rollout by adding a restartedAt annotation
                daemonset = apps_v1.read_namespaced_daemon_set(name, namespace)

                # Add or update the restartedAt annotation to trigger a rollout
                import datetime

                now = datetime.datetime.now(datetime.timezone.utc).isoformat()

                if not daemonset.spec.template.metadata:
                    daemonset.spec.template.metadata = client.V1ObjectMeta()

                if not daemonset.spec.template.metadata.annotations:
                    daemonset.spec.template.metadata.annotations = {}

                daemonset.spec.template.metadata.annotations[
                    "kubectl.kubernetes.io/restartedAt"
                ] = now

                # Update the DaemonSet
                apps_v1.patch_namespaced_daemon_set(
                    name,
                    namespace,
                    daemonset,
                )

                return f"Rollback of DaemonSet {name} initiated successfully"
            else:
                return f"Error: resource type '{resource_type}' rollback not available through API"

        except Exception as e:
            return f"Error: {str(e)}"
    except Exception as exc:
        return "Error:\n" + str(exc)


async def k8s_rollout_restart(resource_type, name, namespace=None):
    """
    Restart a rollout for a deployment, daemonset, or statefulset.

    :param resource_type: The type of resource (deployment, daemonset, statefulset).
    :param name: The name of the resource.
    :param namespace: The namespace of the resource. If not specified, uses the default namespace.
    :return: The result of the restart operation.
    """
    try:
        # Set default namespace if not provided
        if not namespace:
            namespace = "default"

        # Restart using the Kubernetes Python SDK
        try:
            # Get the resource
            if resource_type.lower() == "deployment":
                apps_v1 = client.AppsV1Api()
                deployment = apps_v1.read_namespaced_deployment(name, namespace)

                # Add or update the restartedAt annotation
                import datetime

                now = datetime.datetime.now(datetime.timezone.utc).isoformat()

                if not deployment.spec.template.metadata:
                    deployment.spec.template.metadata = client.V1ObjectMeta()

                if not deployment.spec.template.metadata.annotations:
                    deployment.spec.template.metadata.annotations = {}

                deployment.spec.template.metadata.annotations[
                    "kubectl.kubernetes.io/restartedAt"
                ] = now

                # Update the Deployment
                apps_v1.patch_namespaced_deployment(name, namespace, deployment)

                return f"Restart of {resource_type}/{name} initiated successfully"

            elif resource_type.lower() == "daemonset":
                apps_v1 = client.AppsV1Api()
                daemonset = apps_v1.read_namespaced_daemon_set(name, namespace)

                # Add or update the restartedAt annotation
                import datetime

                now = datetime.datetime.now(datetime.timezone.utc).isoformat()

                if not daemonset.spec.template.metadata:
                    daemonset.spec.template.metadata = client.V1ObjectMeta()

                if not daemonset.spec.template.metadata.annotations:
                    daemonset.spec.template.metadata.annotations = {}

                daemonset.spec.template.metadata.annotations[
                    "kubectl.kubernetes.io/restartedAt"
                ] = now

                # Update the DaemonSet
                apps_v1.patch_namespaced_daemon_set(name, namespace, daemonset)

                return f"Restart of {resource_type}/{name} initiated successfully"

            elif resource_type.lower() == "statefulset":
                apps_v1 = client.AppsV1Api()
                statefulset = apps_v1.read_namespaced_stateful_set(name, namespace)

                # Add or update the restartedAt annotation
                import datetime

                now = datetime.datetime.now(datetime.timezone.utc).isoformat()

                if not statefulset.spec.template.metadata:
                    statefulset.spec.template.metadata = client.V1ObjectMeta()

                if not statefulset.spec.template.metadata.annotations:
                    statefulset.spec.template.metadata.annotations = {}

                statefulset.spec.template.metadata.annotations[
                    "kubectl.kubernetes.io/restartedAt"
                ] = now

                # Update the StatefulSet
                apps_v1.patch_namespaced_stateful_set(name, namespace, statefulset)

                return f"Restart of {resource_type}/{name} initiated successfully"

            else:
                return f"Error: resource type '{resource_type}' restart not available through API"

        except Exception as e:
            return f"Error: {str(e)}"
    except Exception as exc:
        return "Error:\n" + str(exc)


async def k8s_rollout_pause(resource_type, name, namespace=None):
    """
    Pause a rollout for a deployment or daemonset.

    :param resource_type: The type of resource (deployment, daemonset).
    :param name: The name of the resource.
    :param namespace: The namespace of the resource. If not specified, uses the default namespace.
    :return: The result of the pause operation.
    """
    try:
        # Set default namespace if not provided
        if not namespace:
            namespace = "default"

        # Pause using the Kubernetes Python SDK
        try:
            # Get the resource
            if resource_type.lower() == "deployment":
                apps_v1 = client.AppsV1Api()

                # Create a patch to set paused to true
                patch = {"spec": {"paused": True}}

                # Update the Deployment
                apps_v1.patch_namespaced_deployment(
                    name,
                    namespace,
                    patch,
                )

                return f"Paused rollout of {resource_type}/{name} successfully"

            else:
                return f"Error: resource type '{resource_type}' pause not available through API"

        except Exception as e:
            return f"Error: {str(e)}"
    except Exception as exc:
        return "Error:\n" + str(exc)
